"""内存存储：三层记忆的租户隔离存储。

MVP 默认内存实现（离线可测）；Postgres + pgvector 作为演进项，接口保持不变。
所有查询按 tenant_id 过滤 —— 租户隔离是结构性约束，不是约定。
"""
from __future__ import annotations

from app.memory.models import Episode, Lesson, SemanticMemory
from app.semantic.embedding import cosine, embed


class MemoryStore:
    """三层记忆的内存存储（租户隔离）。"""

    def __init__(self) -> None:
        self._episodes: dict[str, list[Episode]] = {}
        self._semantic: dict[str, list[SemanticMemory]] = {}
        self._lessons: dict[str, dict[str, Lesson]] = {}

    # ---- Episode ----
    def add_episode(self, episode: Episode) -> None:
        self._episodes.setdefault(episode.tenant_id, []).append(episode)

    def episodes(self, tenant_id: str) -> list[Episode]:
        return list(self._episodes.get(tenant_id, []))

    # ---- Semantic ----
    def add_semantic(self, mem: SemanticMemory) -> None:
        if not mem.embedding:
            mem.embedding = embed(mem.content)
        self._semantic.setdefault(mem.tenant_id, []).append(mem)

    def semantic_search(
        self, tenant_id: str, query: str, top_k: int = 5, min_score: float = 0.0
    ) -> list[tuple[SemanticMemory, float]]:
        qv = embed(query)
        scored = [
            (m, cosine(qv, m.embedding))
            for m in self._semantic.get(tenant_id, [])
            if m.status == "admitted"
        ]
        scored = [(m, s) for m, s in scored if s >= min_score]
        scored.sort(key=lambda x: -x[1])
        return scored[:top_k]

    def semantic_all(self, tenant_id: str) -> list[SemanticMemory]:
        return list(self._semantic.get(tenant_id, []))

    # ---- Lesson ----
    def upsert_lesson(self, lesson: Lesson) -> None:
        self._lessons.setdefault(lesson.tenant_id, {})[lesson.id] = lesson

    def get_lesson(self, tenant_id: str, lesson_id: str) -> Lesson | None:
        return self._lessons.get(tenant_id, {}).get(lesson_id)

    def lessons(self, tenant_id: str) -> list[Lesson]:
        return list(self._lessons.get(tenant_id, {}).values())

    def record_outcome(self, tenant_id: str, lesson_id: str, helped: bool) -> Lesson | None:
        """记录经验被使用后的结果，hurt_count>0 触发撤销。"""
        lesson = self.get_lesson(tenant_id, lesson_id)
        if lesson is None:
            return None
        lesson.applied_count += 1
        if helped:
            lesson.helped_count += 1
        else:
            lesson.hurt_count += 1
        if lesson.hurt_count > 0:
            lesson.status = "revoked"
        return lesson
