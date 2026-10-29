"""语义层领域模型（Pydantic）。"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


class DimensionDef(BaseModel):
    id: str
    name_cn: str
    table: str
    key_column: str
    value_column: str
    join_sql: str
    aliases: list[str] = Field(default_factory=list)
    hierarchy: list[str] = Field(default_factory=list)
    value_aliases: dict[str, list[str]] = Field(default_factory=dict)
    cardinality_estimate: int = 0


class MetricDef(BaseModel):
    id: str
    name_cn: str
    aliases: list[str] = Field(default_factory=list)
    type: Literal["additive", "semi_additive", "ratio"]
    expression: str | None = None
    source_tables: list[str] = Field(default_factory=list)
    default_time_col: str | None = None
    filters: list[str] = Field(default_factory=list)
    numerator: str | None = None
    denominator: str | None = None
    unit: str = ""
    precision: int = 2
    caliber_cn: str = ""
    owner: str = ""
    version: int = 1
    tags: list[str] = Field(default_factory=list)
    risk_level: Literal["low", "medium", "high"] = "low"
    semantic_version: int = 1

    @field_validator("id")
    @classmethod
    def _snake_case_id(cls, v: str) -> str:
        if not v or not v.replace("_", "").isalnum() or v != v.lower():
            raise ValueError(f"metric id must be lowercase snake_case: {v}")
        return v

    @property
    def is_ratio(self) -> bool:
        return self.type == "ratio"


class Registry(BaseModel):
    semantic_version: int
    dimensions: list[DimensionDef]
    metrics: list[MetricDef]

    @property
    def metric_by_id(self) -> dict[str, MetricDef]:
        return {m.id: m for m in self.metrics}

    @property
    def dimension_by_id(self) -> dict[str, DimensionDef]:
        return {d.id: d for d in self.dimensions}
