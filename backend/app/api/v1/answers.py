"""答案 API：查询问数最终答案（口径/SQL/血缘/图表/结论）。"""
from __future__ import annotations

from fastapi import APIRouter

from app.api.deps import ContainerDep
from app.core.errors import NotFoundError
from app.schemas.question import AnswerOut

router = APIRouter(prefix="/answers", tags=["answers"])


@router.get("/{question_id}", response_model=AnswerOut)
async def get_answer(question_id: str, container: ContainerDep) -> AnswerOut:
    rec = container.run_store.get(question_id)
    if rec is None:
        raise NotFoundError(f"问题不存在: {question_id}")
    ans = rec.answer or {}
    return AnswerOut(
        question_id=question_id,
        level=ans.get("level"),
        value=ans.get("value"),
        rows=ans.get("rows", []),
        caliber=ans.get("caliber", ""),
        sql=ans.get("sql", ""),
        lineage=ans.get("lineage", []),
        chart=ans.get("chart"),
        conclusion=ans.get("conclusion", ""),
        subgoal_trace=ans.get("subgoal_trace", []),
        trace_id=rec.trace_id,
    )
