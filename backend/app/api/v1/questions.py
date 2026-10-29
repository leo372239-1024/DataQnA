"""问数 API：提交问题 + SSE 流式执行。

POST /api/v1/questions         提交问题，返回 question_id
GET  /api/v1/questions/{id}/stream   SSE 流式返回 agent 执行事件
"""
from __future__ import annotations

import hashlib
import json
from collections.abc import AsyncGenerator
from typing import Any

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.api.deps import ContainerDep
from app.core.errors import NotFoundError
from app.core.logging import get_logger
from app.dsl.compiler import SecurityContext
from app.guardrails.audit import AuditEntry
from app.observability.span import Tracer
from app.schemas.question import QuestionCreate, QuestionOut

logger = get_logger()
router = APIRouter(prefix="/questions", tags=["questions"])

# orchestrator 内部事件 type → 前端线缆契约 type（wire contract 单一真相源在
# frontend/src/api/schemas.ts）。必须同时改写 SSE 的 event 名与 data 里的 type 字段，
# 否则前端按 data.type 做 discriminated union 校验会静默丢弃帧。
_EVENT_MAP = {
    "intent_classified": "status",
    "plan_created": "status",
    "subgoal_started": "subgoal",
    "subgoal_completed": "subgoal",
    "answer": "answer",
    "clarification": "clarification",
    "blocked": "blocked",
    "error": "error",
    "done": "done",
}


def _roles_hash(roles: list[str]) -> str:
    return hashlib.sha256("|".join(sorted(roles)).encode()).hexdigest()[:12]


def _sse(event: str, payload: dict[str, Any]) -> str:
    data = json.dumps(payload, ensure_ascii=False, default=str)
    return f"event: {event}\ndata: {data}\n\n"


@router.post("", response_model=QuestionOut, status_code=201)
async def create_question(body: QuestionCreate, container: ContainerDep) -> QuestionOut:
    rec = container.run_store.create(
        question=body.question, tenant_id=body.tenant_id, user_id=body.user_id,
        roles=body.roles, timezone=body.timezone,
    )
    return QuestionOut(
        question_id=rec.question_id, question=rec.question, tenant_id=rec.tenant_id,
        status=rec.status,
    )


@router.get("/{question_id}/stream")
async def stream_question(question_id: str, container: ContainerDep) -> StreamingResponse:
    rec = container.run_store.get(question_id)
    if rec is None:
        raise NotFoundError(f"问题不存在: {question_id}")

    async def gen() -> AsyncGenerator[str, None]:
        tracer = Tracer()
        ctx = SecurityContext(tenant_id=rec.tenant_id)
        roles_hash = _roles_hash(rec.roles)
        answer_payload: dict[str, Any] | None = None
        run_failed = False

        container.run_store.set_status(question_id, "running")
        container.audit.record(AuditEntry(
            tenant_id=rec.tenant_id, actor=rec.user_id, action="ask", trace_id=tracer.trace_id,
            params={"question_id": question_id},
        ))

        try:
            async for ev in container.orchestrator.run(
                rec.question, ctx, roles_hash, tracer=tracer
            ):
                etype = ev.get("type", "")
                if etype == "answer":
                    answer_payload = ev
                if etype == "error":
                    run_failed = True
                if etype == "done":
                    ev = {**ev, "trace_id": tracer.trace_id, "question_id": question_id}
                # 边界翻译：内部事件 type → 前端 contract type，event 名与 data.type 保持一致
                mapped = _EVENT_MAP.get(etype, "status")
                yield _sse(mapped, {**ev, "type": mapped})
        except Exception as e:  # noqa: BLE001
            logger.error("stream_failed", question_id=question_id, error=str(e))
            run_failed = True
            yield _sse("error", {"type": "error", "error": {
                "code": "INTERNAL", "detail": str(e), "trace_id": tracer.trace_id}})
            yield _sse("done", {"type": "done", "trace_id": tracer.trace_id,
                                "question_id": question_id})
        finally:
            container.trace_store.put(tracer)
            container.run_store.set_status(question_id, "failed" if run_failed else "done")
            if answer_payload is not None:
                container.run_store.set_answer(question_id, answer_payload, tracer.trace_id)
            container.audit.record(AuditEntry(
                tenant_id=rec.tenant_id, actor=rec.user_id, action="ask",
                trace_id=tracer.trace_id,
                params={"question_id": question_id},
                result_code="ERROR" if run_failed else "OK",
            ))

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
