"""QueryDSL：LLM 理解与确定性执行之间的结构化契约（Pydantic）。"""
from __future__ import annotations

from datetime import date
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field, PrivateAttr, ValidationInfo, field_validator


class CompareOp(StrEnum):
    PREV_PERIOD = "prev_period"
    SAME_PERIOD_LY = "same_period_ly"


class MetricRef(BaseModel):
    metric_id: str
    semantic_version: int
    aggregation: Literal["sum", "count", "count_distinct", "avg", "max", "min"] = "sum"


class DimensionRef(BaseModel):
    dimension_id: str
    drill_level: int = 0


class TimeWindow(BaseModel):
    start_date: date
    end_date: date  # EXCLUSIVE
    granularity: Literal["day", "week", "month", "quarter", "year"] = "day"
    compare: CompareOp | None = None
    compare_n: int = 1

    @field_validator("end_date")
    @classmethod
    def _end_after_start(cls, v: date, info: ValidationInfo) -> date:
        s = info.data.get("start_date")
        if s is not None and v <= s:
            raise ValueError("end_date must be > start_date")
        return v


class Filter(BaseModel):
    dimension_id: str
    operator: Literal["in", "eq", "gte", "lte", "between"]
    values: list[str | float]


class Order(BaseModel):
    target: str  # metric_id or dimension_id
    direction: Literal["asc", "desc"] = "desc"


class AttributionSpec(BaseModel):
    by_dimension: str
    baseline_window: TimeWindow | None = None


class QueryDSL(BaseModel):
    version: Literal[1] = 1
    metrics: list[MetricRef]
    dimensions: list[DimensionRef] = Field(default_factory=list)
    time: TimeWindow
    filters: list[Filter] = Field(default_factory=list)
    order: list[Order] = Field(default_factory=list)
    limit: int | None = None
    having: list[Filter] = Field(default_factory=list)
    semantic_version: int
    attribution: AttributionSpec | None = None
    _raw_question: str = PrivateAttr(default="")

    @field_validator("metrics")
    @classmethod
    def _non_empty_metrics(cls, v: list[MetricRef]) -> list[MetricRef]:
        if not v:
            raise ValueError("metrics must be non-empty")
        return v
