"""Span 模型 + Tracer：每次用户请求一条 trace，每个图节点至少一个 span。

- 一次 N 个 LLM 调用的节点发出 N 个 llm 子 span（不折叠，保留成本归因）。
- sql_exec span 必须记录 scanned_bytes（缺失是插桩 bug）。
- trace_id 经 SSE 暴露给前端，实时视图与持久化 trace 是同一对象。
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Literal

SpanKind = Literal[
    "intent", "plan", "route", "dsl", "sql_exec", "tool", "llm", "guard", "reflection"
]
SpanStatus = Literal["ok", "error", "blocked"]


@dataclass
class Span:
    trace_id: str
    span_id: str
    kind: SpanKind
    name: str
    start_ts: float
    parent_span_id: str | None = None
    status: SpanStatus = "ok"
    duration_ms: float = 0.0
    token_in: int = 0
    token_out: int = 0
    model: str = ""
    scanned_bytes: int = 0
    failure_code: str | None = None
    asset_id: str | None = None
    semantic_version: int | None = None
    meta: dict[str, Any] = field(default_factory=dict)

    def finish(self, *, status: SpanStatus = "ok", failure_code: str | None = None) -> None:
        self.duration_ms = (time.monotonic() - self.start_ts) * 1000
        self.status = status
        if failure_code is not None:
            self.failure_code = failure_code

    def to_dict(self) -> dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
            "kind": self.kind,
            "name": self.name,
            "status": self.status,
            "duration_ms": round(self.duration_ms, 3),
            "token_in": self.token_in,
            "token_out": self.token_out,
            "model": self.model,
            "scanned_bytes": self.scanned_bytes,
            "failure_code": self.failure_code,
            "asset_id": self.asset_id,
            "semantic_version": self.semantic_version,
        }


class Tracer:
    """单请求 trace 收集器。span 存入内存，接口与 Postgres span 表一致。"""

    def __init__(self, trace_id: str | None = None) -> None:
        self.trace_id = trace_id or uuid.uuid4().hex[:16]
        self._spans: list[Span] = []
        self._stack: list[str] = []

    def start(
        self,
        kind: SpanKind,
        name: str,
        *,
        parent_span_id: str | None = None,
        token_in: int = 0,
        token_out: int = 0,
        model: str = "",
        scanned_bytes: int = 0,
        asset_id: str | None = None,
        semantic_version: int | None = None,
    ) -> Span:
        parent = parent_span_id or (self._stack[-1] if self._stack else None)
        span = Span(
            trace_id=self.trace_id,
            span_id=uuid.uuid4().hex[:12],
            kind=kind,
            name=name,
            start_ts=time.monotonic(),
            parent_span_id=parent,
            token_in=token_in,
            token_out=token_out,
            model=model,
            scanned_bytes=scanned_bytes,
            asset_id=asset_id,
            semantic_version=semantic_version,
        )
        self._spans.append(span)
        return span

    def spans(self) -> list[Span]:
        return list(self._spans)

    def to_dicts(self) -> list[dict[str, Any]]:
        return [s.to_dict() for s in self._spans]
