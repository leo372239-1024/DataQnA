"""审计日志：每次工具调用/查询都记录 who/when/which/params(脱敏)/result_code。

PII 在写入前脱敏（源头脱敏，非渲染时脱敏）。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from app.guardrails.desensitize import desensitize


@dataclass
class AuditEntry:
    tenant_id: str
    actor: str
    action: str  # 工具/查询名
    params: dict[str, Any] = field(default_factory=dict)
    result_code: str = "OK"
    trace_id: str = ""
    ts: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_record(self) -> dict[str, Any]:
        """持久化形态：参数已脱敏。"""
        return {
            "tenant_id": self.tenant_id,
            "actor": self.actor,
            "action": self.action,
            "params": desensitize(self.params),
            "result_code": self.result_code,
            "trace_id": self.trace_id,
            "ts": self.ts.isoformat(),
        }


class AuditLogger:
    """审计日志器。MVP 内存实现，接口与 Postgres 版一致。"""

    def __init__(self) -> None:
        self._records: list[dict[str, Any]] = []

    def record(self, entry: AuditEntry) -> None:
        self._records.append(entry.to_record())

    def records(self, tenant_id: str | None = None) -> list[dict[str, Any]]:
        if tenant_id is None:
            return list(self._records)
        return [r for r in self._records if r["tenant_id"] == tenant_id]
