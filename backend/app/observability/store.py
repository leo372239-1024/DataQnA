"""Trace 存储：trace_id → span 树的持久化（MVP 内存实现）。

实时视图（SSE 暴露的 trace_id）与持久化 trace 是同一对象，前端按 trace_id 拉取。
"""
from __future__ import annotations

import threading

from app.observability.span import Tracer


class TraceStore:
    """trace 内存存储（线程安全）。"""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._traces: dict[str, Tracer] = {}

    def put(self, tracer: Tracer) -> None:
        with self._lock:
            self._traces[tracer.trace_id] = tracer

    def get(self, trace_id: str) -> Tracer | None:
        with self._lock:
            return self._traces.get(trace_id)

    def all_ids(self) -> list[str]:
        with self._lock:
            return list(self._traces.keys())
