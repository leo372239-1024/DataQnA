"""三层路由：权限交集 → 别名精确命中 → 向量召回 → 候选内重排。

Stage 0 权限交集在任何模型调用前结构性剔除越权资产（Confused Deputy 防线）。
"""
from __future__ import annotations

from app.core.config import settings
from app.routing.models import Asset, RoutingResult
from app.routing.registry import AssetRegistry
from app.routing.rerank import Reranker
from app.semantic.embedding import cosine, embed


class Router:
    """资产路由器。caller_roles 为空集合表示无任何特殊角色（仅公共资产可见）。"""

    def __init__(
        self,
        registry: AssetRegistry,
        *,
        margin: float | None = None,
        top_k: int = 10,
        reranker: Reranker | None = None,
    ) -> None:
        self.registry = registry
        self.margin = margin if margin is not None else settings.route_margin
        self.top_k = top_k
        self._negative: dict[tuple[str, str], float] = {}
        self.reranker = reranker or Reranker(margin=self.margin, penalty_fn=self._penalty)

    # ---- 负记忆（自改进路由）----

    def _penalty(self, request_text: str, asset_id: str) -> float:
        return self._negative.get((request_text, asset_id), 0.0)

    def record_negative(self, request_text: str, asset_id: str, penalty: float = 0.5) -> None:
        """记录「请求 X 不应路由到资产 Y」的负记忆，供 Stage 1/3 惩罚。"""
        self._negative[(request_text, asset_id)] = penalty

    # ---- 路由主流程 ----

    async def route(self, request_text: str, caller_roles: set[str], *,
                    baseline: bool = False) -> RoutingResult:
        # Stage 0：权限交集（结构性，先于一切）
        visible = self._permission_filter(caller_roles)
        visible_ids = {a.id for a in visible}

        # Stage 1：别名命中（对全部资产，先于权限裁剪——用于识别「越权意图」并阻断）。
        # 若最优命中资产在 caller 权限之外，直接返回权限拒绝，绝不静默降级到更弱的公开资产
        # （Confused Deputy 防线）。
        hit = self._alias_match(request_text, self.registry.assets)
        if hit is not None:
            if hit.id not in visible_ids:
                return RoutingResult(
                    confidence=0.0, stage="permission",
                    clarification=f"「{hit.name}」需要更高权限，当前角色无权调用",
                    evidence={"blocked_asset": hit.id},
                )
            return RoutingResult(
                asset_id=hit.id, asset=hit, confidence=0.95, stage="alias",
                evidence={"alias": request_text},
            )

        if not visible:
            return RoutingResult(
                confidence=0.0, stage="permission", clarification="没有可用的资产（权限不足）"
            )

        # 基线模式：仅别名短路，不做向量召回/精排（用于 A/B 评测）
        if baseline:
            return RoutingResult(
                confidence=0.0, stage="alias",
                clarification="基线模式（仅别名）未命中",
            )

        # Stage 2：向量召回 top-k
        recalled = self._vector_recall(request_text, visible)
        if not recalled:
            return RoutingResult(
                confidence=0.0, stage="vector", clarification="未找到匹配的资产"
            )

        # Stage 3：候选内重排（歧义 → 澄清）
        choice, conf = await self.reranker.rerank(request_text, recalled)
        if choice is None:
            return RoutingResult(
                confidence=conf, stage="rerank",
                clarification="请求可能对应多个资产，请确认",
                candidates=[c.id for c in recalled[:3]],
                evidence={"top_scores": [
                    {"id": c.id, "name": c.name} for c in recalled[:3]
                ]},
            )
        asset = self.registry.get(choice)
        return RoutingResult(
            asset_id=choice, asset=asset, confidence=conf, stage="rerank",
            evidence={"recalled": [c.id for c in recalled]},
        )

    # ---- Stage 实现 ----

    def _permission_filter(self, caller_roles: set[str]) -> list[Asset]:
        out = []
        for a in self.registry.assets:
            if a.deprecated:
                continue
            # 资产无权限要求（permissions 空）→ 人人可用；否则要求 caller_roles 覆盖其全部权限
            if not a.permissions or set(a.permissions) <= caller_roles:
                out.append(a)
        return out

    def _alias_match(self, request_text: str, assets: list[Asset]) -> Asset | None:
        """别名匹配：精确相等优先；否则「位置最早 → 别名最长」决胜（中文动作词常居句首）。

        被负记忆（该请求→该资产）命中的资产不参与 Stage 1 短路，回落向量召回以便惩罚生效。
        """
        stripped = request_text.strip()
        # 1) 精确相等（名称或别名）
        for a in assets:
            if self._penalty(request_text, a.id) > 0.0:
                continue
            if stripped in [a.name, *a.aliases]:
                return a
        # 2) 位置最早 → 别名最长
        best: tuple[int, int, Asset] | None = None  # (pos, -len, asset)
        for a in assets:
            if self._penalty(request_text, a.id) > 0.0:
                continue
            for al in [a.name, *a.aliases]:
                if not al:
                    continue
                pos = request_text.find(al)
                if pos < 0:
                    continue
                key = (pos, -len(al))
                if best is None or key < (best[0], best[1]):
                    best = (pos, -len(al), a)
        return best[2] if best else None

    def _vector_recall(self, request_text: str, visible: list[Asset]) -> list[Asset]:
        req_vec = embed(request_text)
        scored = sorted(
            visible,
            key=lambda a: cosine(req_vec, self.registry.vector(a.id)),
            reverse=True,
        )
        return scored[: self.top_k]
