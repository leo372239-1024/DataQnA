"""评测触发/结果响应模型（占位，评测跑分器在阶段 5 实现）。"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class EvalRunRequest(BaseModel):
    suite: str = Field(default="gold")  # gold | routing | redteam | reflection | longtask
    level: str = Field(default="L1-L5")  # L1 | L2 | L3 | L4 | L5 | L1-L5
    baseline: str = Field(default="on")  # on | off


class EvalRunOut(BaseModel):
    run_id: str
    suite: str
    status: str  # running | done | failed
    summary: dict[str, Any] = Field(default_factory=dict)
