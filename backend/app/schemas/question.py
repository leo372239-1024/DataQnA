"""问数请求/响应模型。"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator


class QuestionCreate(BaseModel):
    """提交问数请求。

    说明：MVP 阶段 tenant_id / user_id / roles 由请求体携带；生产环境应由认证主体
    （JWT principal）派生，绝不信任客户端声明的角色（见 spec/api-conventions.md Auth）。
    """

    question: str = Field(min_length=1, max_length=2000)
    tenant_id: str = Field(default="t1", min_length=1, max_length=64)
    user_id: str = Field(default="demo", max_length=64)
    roles: list[str] = Field(default_factory=lambda: ["analyst"])
    timezone: str = Field(default="Asia/Shanghai")

    @field_validator("question")
    @classmethod
    def _strip_question(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("question 不能为空")
        return v


class QuestionOut(BaseModel):
    question_id: str
    question: str
    tenant_id: str
    status: str
    trace_id: str | None = None


class AnswerOut(BaseModel):
    question_id: str
    level: str | None = None
    value: float | None = None
    rows: list[dict[str, Any]] = Field(default_factory=list)
    caliber: str = ""
    sql: str = ""
    lineage: list[dict[str, Any]] = Field(default_factory=list)
    chart: dict[str, Any] | None = None
    conclusion: str = ""
    subgoal_trace: list[dict[str, Any]] = Field(default_factory=list)
    trace_id: str | None = None
