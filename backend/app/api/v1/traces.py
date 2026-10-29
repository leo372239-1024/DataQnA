"""Trace API：按 trace_id 拉取 span 树。"""
from __future__ import annotations

from fastapi import APIRouter

from app.api.deps import ContainerDep
from app.core.errors import NotFoundError
from app.schemas.trace import TraceOut

router = APIRouter(prefix="/traces", tags=["traces"])


@router.get("/{trace_id}", response_model=TraceOut)
async def get_trace(trace_id: str, container: ContainerDep) -> TraceOut:
    tracer = container.trace_store.get(trace_id)
    if tracer is None:
        raise NotFoundError(f"trace 不存在: {trace_id}")
    return TraceOut(trace_id=trace_id, spans=tracer.to_dicts())
