"""语义层只读响应模型。"""
from __future__ import annotations

from pydantic import BaseModel, Field

from app.semantic.models import DimensionDef, MetricDef


class MetricOut(BaseModel):
    id: str
    name_cn: str
    aliases: list[str] = Field(default_factory=list)
    type: str
    unit: str = ""
    caliber_cn: str = ""
    owner: str = ""
    version: int = 1
    tags: list[str] = Field(default_factory=list)
    risk_level: str = "low"

    @classmethod
    def from_def(cls, m: MetricDef) -> MetricOut:
        return cls(
            id=m.id, name_cn=m.name_cn, aliases=m.aliases, type=m.type, unit=m.unit,
            caliber_cn=m.caliber_cn, owner=m.owner, version=m.version, tags=m.tags,
            risk_level=m.risk_level,
        )


class LineageNode(BaseModel):
    metric_id: str
    name_cn: str
    version: int


class MetricDetailOut(MetricOut):
    expression: str | None = None
    numerator: str | None = None
    denominator: str | None = None
    source_tables: list[str] = Field(default_factory=list)
    default_time_col: str | None = None
    lineage: list[LineageNode] = Field(default_factory=list)


class DimensionOut(BaseModel):
    id: str
    name_cn: str
    aliases: list[str] = Field(default_factory=list)
    hierarchy: list[str] = Field(default_factory=list)
    cardinality_estimate: int = 0

    @classmethod
    def from_def(cls, d: DimensionDef) -> DimensionOut:
        return cls(
            id=d.id, name_cn=d.name_cn, aliases=d.aliases, hierarchy=d.hierarchy,
            cardinality_estimate=d.cardinality_estimate,
        )
