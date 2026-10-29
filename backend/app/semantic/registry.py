"""MetricRegistry：加载 YAML 真相源 + 校验 I1–I7 不变式 + 查询。"""
from __future__ import annotations

from pathlib import Path

import yaml

from app.semantic.models import DimensionDef, MetricDef, Registry

# 白名单表：指标 source_tables 与维度 table 必须在此（I6）
TABLE_WHITELIST = {
    "fact_order", "dim_region", "dim_category", "dim_channel",
    "dim_order_payment", "dim_device", "dim_user",
}


class RegistryValidationError(ValueError):
    """不变式校验失败。"""


def load_registry(path: str | Path) -> Registry:
    with open(path, encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    return Registry(**raw)


def validate_registry(reg: Registry) -> None:
    """校验 I1–I7。任一失败抛 RegistryValidationError。"""
    metric_ids = [m.id for m in reg.metrics]
    dim_ids = {d.id for d in reg.dimensions}

    # I1: id 唯一
    if len(metric_ids) != len(set(metric_ids)):
        raise RegistryValidationError("I1: 指标 id 重复")
    if len(dim_ids) != len(reg.dimensions):
        raise RegistryValidationError("I1: 维度 id 重复")

    for m in reg.metrics:
        # I2: caliber 非空
        if not m.caliber_cn:
            raise RegistryValidationError(f"I2: 指标 {m.id} 缺少口径中文 caliber_cn")
        # I3: ratio 有分子分母
        if m.is_ratio and (m.numerator not in metric_ids or m.denominator not in metric_ids):
            raise RegistryValidationError(f"I3: 比率指标 {m.id} 分子/分母未注册")
        # I6: source_tables 白名单
        for t in m.source_tables:
            if t not in TABLE_WHITELIST:
                raise RegistryValidationError(f"I6: 指标 {m.id} 引用了未白名单表 {t}")

    # I5: 别名两两不相交
    seen: dict[str, str] = {}
    for m in reg.metrics:
        for a in m.aliases:
            if a in seen and seen[a] != m.id:
                raise RegistryValidationError(f"I5: 别名 '{a}' 同时属于 {seen[a]} 与 {m.id}")
            seen[a] = m.id

    # I7: hierarchy 成员是已注册维度
    for d in reg.dimensions:
        for h in d.hierarchy:
            if h not in dim_ids:
                raise RegistryValidationError(f"I7: 维度 {d.id} 的层级成员 {h} 未注册")


class MetricRegistry:
    """运行时注册表：加载 + 缓存 + 查询。"""

    def __init__(self, reg: Registry) -> None:
        validate_registry(reg)
        self._reg = reg
        self._alias_index: dict[str, str] = {}
        for m in reg.metrics:
            for a in m.aliases:
                self._alias_index[a] = m.id

    @classmethod
    def from_yaml(cls, path: str | Path) -> MetricRegistry:
        return cls(load_registry(path))

    @property
    def semantic_version(self) -> int:
        return self._reg.semantic_version

    def get_metric(self, metric_id: str) -> MetricDef:
        m = self._reg.metric_by_id.get(metric_id)
        if m is None:
            raise KeyError(f"未注册指标: {metric_id}")
        return m

    def get_dimension(self, dimension_id: str) -> DimensionDef:
        d = self._reg.dimension_by_id.get(dimension_id)
        if d is None:
            raise KeyError(f"未注册维度: {dimension_id}")
        return d

    def alias_to_metric(self, alias: str) -> str | None:
        """精确别名 → 指标 id（无则 None）。"""
        return self._alias_index.get(alias)

    @property
    def metrics(self) -> list[MetricDef]:
        return self._reg.metrics

    @property
    def dimensions(self) -> list[DimensionDef]:
        return self._reg.dimensions
