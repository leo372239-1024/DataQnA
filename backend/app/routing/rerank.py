"""重排器：在候选内选择（ranking，非 generation）。

- LLM 模式（provider=openai_compat）：结构化输出约束 choice ∈ 候选 id。
- 离线模式（stub）：确定性打分（向量余弦 + 域/别名加成 - 负记忆惩罚）。
两者都绝不输出候选列表之外的 id。
"""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from app.core.config import settings
from app.core.logging import get_logger
from app.llm.gateway import get_gateway
from app.routing.models import Asset
from app.semantic.embedding import cosine, embed

logger = get_logger()

# 负记忆惩罚函数签名：(request_text, asset_id) -> 惩罚值
PenaltyFn = Callable[[str, str], float]


def _bigram_overlap(request_text: str, asset_text: str) -> float:
    """请求 bigram 被资产文本覆盖的召回率（containment）。

    路由场景下更有判别力：衡量「资产能在多大程度上解释请求」，而非对称相似度。
    分母取请求 bigram 数，故请求中的判别性短语（如「去年同期」「经营业绩」）权重更高。
    """
    gq = [request_text[i : i + 2] for i in range(len(request_text) - 1)]
    if not gq:
        return 0.0
    gb = {asset_text[i : i + 2] for i in range(len(asset_text) - 1)}
    return sum(1 for g in gq if g in gb) / len(gq)


def _validate_rerank_output(candidate_ids: list[str]) -> Callable[[Any], dict[str, Any]]:
    """返回校验器：解析 LLM 结构化输出并强制 choice ∈ 候选。"""

    def _validate(parsed: Any) -> dict[str, Any]:
        import json

        if isinstance(parsed, str):
            parsed = json.loads(parsed)
        if not isinstance(parsed, dict):
            raise ValueError("rerank 输出必须是对象")
        choice = parsed.get("choice")
        if choice not in candidate_ids:
            raise ValueError(f"choice {choice!r} 不在候选 {candidate_ids} 内")
        conf = float(parsed.get("confidence", 0.0))
        return {"choice": choice, "confidence": max(0.0, min(1.0, conf))}

    return _validate


class Reranker:
    """候选内重排。返回 (choice, confidence)；歧义时 choice 为 None。"""

    def __init__(self, margin: float | None = None, penalty_fn: PenaltyFn | None = None) -> None:
        self.margin = margin if margin is not None else settings.route_margin
        self._penalty = penalty_fn or (lambda _req, _aid: 0.0)

    async def rerank(
        self, request_text: str, candidates: list[Asset]
    ) -> tuple[str | None, float]:
        if not candidates:
            return None, 0.0
        if len(candidates) == 1:
            return candidates[0].id, 0.95

        if settings.llm_provider == "openai_compat":
            return await self._llm_rerank(request_text, candidates)

        return self._deterministic_rerank(request_text, candidates)

    def _deterministic_rerank(
        self, request_text: str, candidates: list[Asset]
    ) -> tuple[str | None, float]:
        req_vec = embed(request_text)
        scores: list[tuple[float, Asset]] = []
        for c in candidates:
            base = cosine(req_vec, embed(c.embedding_text()))
            # 字符 bigram 重合度：比 hashed cosine 对中文语义更鲁棒，作为主导信号
            overlap = _bigram_overlap(request_text, c.embedding_text())
            bonus = 0.0
            for dom in c.domains:
                if dom in request_text:
                    bonus += 0.05
            for al in c.aliases:
                if al in request_text:
                    bonus += 0.1
            penalty = self._penalty(request_text, c.id)
            scores.append((0.4 * base + 0.6 * overlap + bonus - penalty, c))
        scores.sort(key=lambda x: -x[0])
        top1, top2 = scores[0][0], scores[1][0] if len(scores) > 1 else 1.0
        # 相对差距判定：确定性打分尺度压缩（0~0.5），绝对阈值会失真；
        # 用「top1 相对 top2 领先幅度」判断是否歧义，跨尺度更稳健。
        if top1 <= 0.0 or (top1 - top2) / top1 < self.margin:
            return None, top1
        return scores[0][1].id, min(1.0, top1)

    async def _llm_rerank(
        self, request_text: str, candidates: list[Asset]
    ) -> tuple[str | None, float]:
        candidate_ids = [c.id for c in candidates]
        brief = "\n".join(
            f"- id={c.id} name={c.name} capability={c.capability}" for c in candidates
        )
        gateway = get_gateway()
        from app.llm.base import LLMRequest

        req = LLMRequest(
            system=(
                "你是工具/技能路由器。只从给定候选里选择一个，输出 JSON："
                '{"choice": "<候选id>", "confidence": 0.0~1.0}。禁止输出候选之外的 id。'
            ),
            messages=[
                {"role": "user", "content": f"请求：{request_text}\n候选：\n{brief}"},
            ],
            task="rerank",
            needs_structured=True,
        )
        try:
            out = await gateway.complete_structured(
                req, _validate_rerank_output(candidate_ids), max_retries=1
            )
            # 负记忆惩罚：若命中负记忆，拉低置信度，低于阈值则澄清
            conf = out["confidence"] - self._penalty(request_text, out["choice"])
            if conf < self.margin:
                return None, conf
            return out["choice"], conf
        except Exception as e:  # noqa: BLE001
            logger.warning("llm_rerank_failed", error=str(e))
            return None, 0.0
