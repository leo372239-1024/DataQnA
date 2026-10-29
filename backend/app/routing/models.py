"""路由领域模型：统一资产（skill/tool）+ 路由结果。"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class Asset(BaseModel):
    """统一资产模型：skill 与 tool 对路由器是同一种资产，仅执行目标不同。"""

    id: str
    kind: Literal["skill", "tool"]
    name: str
    description: str
    aliases: list[str] = Field(default_factory=list)
    domains: list[str] = Field(default_factory=list)
    capability: str  # 一行「它能做什么」，用于 embedding 与 rerank
    params_schema: dict[str, Any] = Field(default_factory=dict)
    permissions: list[str] = Field(default_factory=list)  # 需要的角色；空 = 无特殊范围
    risk: Literal["low", "medium", "high"] = "low"
    version: int = 1
    deprecated: bool = False
    requires_confirmation: bool = False
    success_rate: float = 1.0
    avg_latency_ms: float = 0.0
    last_used_at: datetime | None = None

    @field_validator("id")
    @classmethod
    def _snake_case_id(cls, v: str) -> str:
        if not v or not v.replace("_", "").isalnum() or v != v.lower():
            raise ValueError(f"asset id must be lowercase snake_case: {v}")
        return v

    def embedding_text(self) -> str:
        """embedding 输入 = name + capability + aliases（spec 要求，非仅 description）。"""
        return " ".join([self.name, self.capability, *self.aliases])


class RoutingResult(BaseModel):
    """路由结果：命中资产或澄清。"""

    asset_id: str | None = None
    asset: Asset | None = None
    confidence: float = 0.0
    stage: str = ""  # permission | alias | vector | rerank
    evidence: dict[str, Any] = Field(default_factory=dict)
    clarification: str | None = None
    candidates: list[str] = Field(default_factory=list)  # 澄清时给出候选 id

    @property
    def resolved(self) -> bool:
        return self.asset_id is not None
