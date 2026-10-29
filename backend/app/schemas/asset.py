"""资产（skill/tool）只读响应模型。"""
from __future__ import annotations

from pydantic import BaseModel, Field

from app.routing.models import Asset


class AssetOut(BaseModel):
    id: str
    kind: str
    name: str
    description: str
    aliases: list[str] = Field(default_factory=list)
    domains: list[str] = Field(default_factory=list)
    capability: str
    permissions: list[str] = Field(default_factory=list)
    risk: str
    deprecated: bool = False
    requires_confirmation: bool = False

    @classmethod
    def from_asset(cls, a: Asset) -> AssetOut:
        return cls(
            id=a.id, kind=a.kind, name=a.name, description=a.description,
            aliases=a.aliases, domains=a.domains, capability=a.capability,
            permissions=a.permissions, risk=a.risk, deprecated=a.deprecated,
            requires_confirmation=a.requires_confirmation,
        )
