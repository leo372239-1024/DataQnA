"""Agent 编排状态模型。"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Literal

from app.dsl.models import QueryDSL


@dataclass
class IntentFrame:
    level: Literal["L1", "L2", "L3", "L4", "L5"]
    metric_ids: list[str] = field(default_factory=list)
    dimension_ids: list[str] = field(default_factory=list)
    start_date: date | None = None
    end_date: date | None = None
    granularity: str = "day"
    compare: str | None = None
    attribution: bool = False
    raw_question: str = ""
    evidence: dict[str, Any] = field(default_factory=dict)


@dataclass
class SubgoalResult:
    subgoal_id: str
    status: Literal["ok", "failed", "ambiguous"] = "ok"
    rows: list[dict[str, Any]] = field(default_factory=list)
    columns: list[str] = field(default_factory=list)
    dsl: QueryDSL | None = None
    sql: str = ""
    scanned_bytes: int = 0
    latency_ms: float = 0.0
    failure_code: str | None = None
    evidence: dict[str, Any] = field(default_factory=dict)


@dataclass
class Subgoal:
    id: str
    name: str
    kind: Literal["query", "compare", "attribution", "report"]
    deps: list[str] = field(default_factory=list)
    dsl: QueryDSL | None = None
    status: Literal["pending", "running", "ok", "failed"] = "pending"
    result: SubgoalResult | None = None


@dataclass
class Plan:
    plan_id: str
    intent: IntentFrame
    subgoals: list[Subgoal] = field(default_factory=list)
    dependency: dict[str, list[str]] = field(default_factory=dict)
    parent_plan_id: str | None = None
    replan_reason: str | None = None


@dataclass
class AgentState:
    question: str
    tenant_id: str
    user_id: str = ""
    roles: list[str] = field(default_factory=list)
    session_id: str = ""
    intent: IntentFrame | None = None
    plan: Plan | None = None
    plan_history: list[Plan] = field(default_factory=list)
    results: dict[str, SubgoalResult] = field(default_factory=dict)
    replan_count: int = 0
    max_steps: int = 12
