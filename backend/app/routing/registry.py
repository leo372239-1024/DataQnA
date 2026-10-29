"""AssetRegistry：加载资产真相源 YAML + 别名索引 + 能力向量预计算。"""
from __future__ import annotations

from pathlib import Path

import yaml

from app.routing.models import Asset
from app.semantic.embedding import embed


class AssetRegistryValidationError(ValueError):
    """资产注册表校验失败。"""


def load_assets(path: str | Path) -> list[Asset]:
    with open(path, encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    items = raw.get("assets", raw if isinstance(raw, list) else [])
    return [Asset(**a) for a in items]


def validate_assets(assets: list[Asset]) -> None:
    ids = [a.id for a in assets]
    if len(ids) != len(set(ids)):
        raise AssetRegistryValidationError("资产 id 重复")
    # 别名两两不相交（同一资产内可重复，跨资产不可）
    seen: dict[str, str] = {}
    for a in assets:
        for al in a.aliases:
            if al in seen and seen[al] != a.id:
                raise AssetRegistryValidationError(f"别名 '{al}' 同时属于 {seen[al]} 与 {a.id}")
            seen[al] = a.id
    # kind 一致性：skill/tool
    for a in assets:
        if a.kind not in ("skill", "tool"):
            raise AssetRegistryValidationError(f"资产 {a.id} kind 非法: {a.kind}")
        if not a.capability:
            raise AssetRegistryValidationError(f"资产 {a.id} 缺少 capability")


class AssetRegistry:
    """运行时资产注册表：加载 + 别名索引 + 预计算能力向量。"""

    def __init__(self, assets: list[Asset]) -> None:
        validate_assets(assets)
        self._assets = {a.id: a for a in assets}
        self._alias_index: dict[str, str] = {}
        self._vectors: dict[str, list[float]] = {}
        for a in assets:
            for al in a.aliases:
                self._alias_index[al] = a.id
            self._vectors[a.id] = embed(a.embedding_text())

    @classmethod
    def from_yaml(cls, path: str | Path) -> AssetRegistry:
        return cls(load_assets(path))

    @property
    def assets(self) -> list[Asset]:
        return list(self._assets.values())

    def get(self, asset_id: str) -> Asset | None:
        return self._assets.get(asset_id)

    def alias_to_asset(self, alias: str) -> str | None:
        return self._alias_index.get(alias)

    def vector(self, asset_id: str) -> list[float]:
        return self._vectors[asset_id]
