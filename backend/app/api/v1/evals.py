"""评测 API：触发评测跑分 + 查询结果。

跑分器在阶段 5（evals）实现；本端点先把契约定下来，未实现时返回明确的状态码。
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter

from app.api.deps import ContainerDep
from app.schemas.eval import EvalRunOut, EvalRunRequest

router = APIRouter(prefix="/evals", tags=["evals"])


@router.post("/run", response_model=EvalRunOut, status_code=202)
async def run_eval(body: EvalRunRequest, container: ContainerDep) -> EvalRunOut:
    run_id = uuid.uuid4().hex[:12]
    try:
        from app.evals.runner import run_suite

        summary = await run_suite(
            suite=body.suite, level=body.level, baseline=body.baseline == "on",
            registry=container.registry, gateway=container.gateway,
        )
        return EvalRunOut(run_id=run_id, suite=body.suite, status="done", summary=summary)
    except ImportError:
        # 跑分器尚未实现（阶段 5），返回占位结果
        return EvalRunOut(
            run_id=run_id, suite=body.suite, status="failed",
            summary={"error": "eval runner not implemented yet", "detail": "阶段 5 实现"},
        )
