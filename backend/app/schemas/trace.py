"""Trace 响应模型。"""
from __future__ import annotations

from pydantic import BaseModel, Field


class SpanOut(BaseModel):
    trace_id: str
    span_id: str
    parent_span_id: str | None = None
    kind: str
    name: str
    status: str
    duration_ms: float = 0.0
    token_in: int = 0
    token_out: int = 0
    model: str = ""
    scanned_bytes: int = 0
    failure_code: str | None = None
    asset_id: str | None = None
    semantic_version: int | None = None


class TraceOut(BaseModel):
    trace_id: str
    spans: list[SpanOut] = Field(default_factory=list)
