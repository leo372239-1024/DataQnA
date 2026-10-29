"""反思循环：确定性抽取优先 → LLM 蒸馏 → 入池门槛 → 写回。

设计原则（spec）：
1. 确定性优先，LLM 次之 —— 候选来自具体信号（别名未命中、schema 错误），
   绝不「请 LLM 通读整条 trace 找洞见」。
2. 无证据不自动应用 —— 每条写回携带 evidence_episode_id，可撤销。
3. 失败是金矿 —— 成功只做别名/实体富化；失败才挖经验。

隐私边界：反思只读 Episode 的摘要（subgoal_summary）与失败码，绝不读原始工具 payload。
"""
from __future__ import annotations

from typing import Any

from app.core.logging import get_logger
from app.memory.failure_codes import CODE_TO_FIX
from app.memory.models import ADMIT_THRESHOLD, Episode, Lesson
from app.memory.store import MemoryStore

logger = get_logger()

# 失败码 → (写回动作, 确定性置信度)
_CODE_ACTION: dict[str, tuple[str, float]] = {
    "NO_MATCH": ("add_alias", 0.85),
    "METRIC_AMBIG": ("enrich_description", 0.60),
    "CONTEXT_LOSS": ("other", 0.50),
    "TOOL_MISUSE": ("enrich_description", 0.70),
    "MULTI_TURN_DRIFT": ("other", 0.50),
    "HALLUCINATED_CALIBER": ("other", 0.50),
    "OVER_BLOCK": ("other", 0.50),
    "RATE_TRAP": ("other", 0.90),
    "COST_OVERFLOW": ("other", 0.50),
}


class ReflectionEngine:
    """反思引擎：从 episode 确定性抽取经验 → 蒸馏 → 入池。"""

    def __init__(self, store: MemoryStore, *, auto_admit: bool = False) -> None:
        self.store = store
        self.auto_admit = auto_admit

    # ---- 主流程 ----

    async def reflect(self, episode: Episode) -> list[Lesson]:
        """反思一条 episode，返回（可能为空的）经验列表。成功且无信号的 episode 返回空。"""
        candidates = self._extract_candidates(episode)  # 1. 确定性抽取（先于 LLM）
        lessons: list[Lesson] = []
        for cand in candidates:
            distilled = await self._distill(episode, cand)  # 2. LLM 蒸馏（仅失败/有候选）
            lesson = self._admit(episode, distilled)        # 3. 入池门槛
            self.store.upsert_lesson(lesson)                # 4. 写回
            lessons.append(lesson)
        return lessons

    # ---- 1. 确定性抽取 ----

    def _extract_candidates(self, episode: Episode) -> list[dict[str, Any]]:
        """只从失败码 + 摘要提取候选，不调 LLM，不读原始 payload。"""
        if episode.outcome != "failure" or not episode.failure_code:
            return []
        action, conf = _CODE_ACTION.get(episode.failure_code, ("other", 0.30))
        return [{
            "action": action,
            "confidence": conf,
            "lesson": CODE_TO_FIX.get(episode.failure_code, "根据失败码改进"),
            "applies_to": self._infer_applies_to(episode),
        }]

    def _infer_applies_to(self, episode: Episode) -> str | None:
        """从摘要中推断经验作用对象（asset_id / metric_id），不触碰原始 payload。"""
        for s in episode.subgoal_summary:
            for key in ("asset_id", "metric_id", "tool_id"):
                if s.get(key):
                    return str(s[key])
        return None

    # ---- 2. LLM 蒸馏（占位：离线模式下仅回传确定性候选，绝不臆造） ----

    async def _distill(self, episode: Episode, candidate: dict[str, Any]) -> dict[str, Any]:
        """LLM 蒸馏是「精炼」而非「发明」：离线/未配置时原样返回确定性候选。"""
        return candidate

    # ---- 3. 入池门槛 ----

    def _admit(self, episode: Episode, candidate: dict[str, Any]) -> Lesson:
        conf = float(candidate["confidence"])
        status = "quarantined"
        if conf >= ADMIT_THRESHOLD:
            status = "admitted" if self.auto_admit else "quarantined"
        return Lesson(
            id=f"lesson_{episode.tenant_id}_{episode.id}",
            tenant_id=episode.tenant_id,
            lesson=candidate["lesson"],
            applies_to=candidate.get("applies_to"),
            action=candidate.get("action", "other"),
            confidence=conf,
            status=status,
            evidence_episode_id=episode.id,
        )
