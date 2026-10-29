"""运行存储：问题 → 上下文 → 答案信封 → trace 的关联（MVP 内存实现）。

接口与 Postgres 持久化版一致，便于后续替换。
"""
from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass
class QuestionRecord:
    question_id: str
    question: str
    tenant_id: str
    user_id: str
    roles: list[str] = field(default_factory=list)
    timezone: str = "Asia/Shanghai"
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    answer: dict[str, Any] | None = None
    trace_id: str | None = None
    status: str = "pending"  # pending | running | done | failed


class RunStore:
    """问题与答案的内存存储（线程安全）。"""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._records: dict[str, QuestionRecord] = {}

    def create(
        self, question: str, tenant_id: str, user_id: str = "",
        roles: list[str] | None = None, timezone: str = "Asia/Shanghai",
    ) -> QuestionRecord:
        qid = uuid.uuid4().hex[:16]
        rec = QuestionRecord(
            question_id=qid, question=question, tenant_id=tenant_id, user_id=user_id,
            roles=roles or [], timezone=timezone,
        )
        with self._lock:
            self._records[qid] = rec
        return rec

    def get(self, question_id: str) -> QuestionRecord | None:
        with self._lock:
            return self._records.get(question_id)

    def set_status(self, question_id: str, status: str) -> None:
        rec = self.get(question_id)
        if rec is not None:
            rec.status = status

    def set_answer(self, question_id: str, answer: dict[str, Any],
                   trace_id: str | None = None) -> None:
        rec = self.get(question_id)
        if rec is not None:
            rec.answer = answer
            rec.trace_id = trace_id
