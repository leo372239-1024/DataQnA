"""聚合表达式解析与率值展开（防率值陷阱）。"""
from __future__ import annotations

import re

from app.core.errors import RateTrapError
from app.semantic.models import MetricDef
from app.semantic.registry import MetricRegistry

# 支持的聚合模式（registry 表达式必须是这三种之一）
_SUM_RE = re.compile(r"^SUM\(\s*(.+?)\s*\)$", re.IGNORECASE)
_COUNT_DISTINCT_RE = re.compile(r"^COUNT\(\s*DISTINCT\s+(.+?)\s*\)$", re.IGNORECASE)
_COUNT_RE = re.compile(r"^COUNT\(\s*(.+?)\s*\)$", re.IGNORECASE)


def parse_aggregate(expression: str) -> tuple[str, str]:
    """解析聚合表达式 → (func, inner)。func ∈ {SUM, COUNT_DISTINCT, COUNT}。"""
    m = _SUM_RE.match(expression)
    if m:
        return "SUM", m.group(1).strip()
    m = _COUNT_DISTINCT_RE.match(expression)
    if m:
        return "COUNT_DISTINCT", m.group(1).strip()
    m = _COUNT_RE.match(expression)
    if m:
        return "COUNT", m.group(1).strip()
    raise ValueError(f"不支持的聚合表达式: {expression}")


def _cond(filters: list[str]) -> str:
    return " AND ".join(f"({f})" for f in filters)


def agg_sql(func: str, inner: str, filters: list[str]) -> str:
    """把聚合函数 + 指标级 filter 编译为条件聚合片段（filters 不进 WHERE）。"""
    if not filters:
        if func == "COUNT_DISTINCT":
            return f"COUNT(DISTINCT {inner})"
        if func == "COUNT":
            return f"COUNT({inner})"
        return f"{func}({inner})"
    c = _cond(filters)
    if func == "SUM":
        return f"SUM(CASE WHEN {c} THEN {inner} ELSE 0 END)"
    if func == "COUNT_DISTINCT":
        return f"COUNT(DISTINCT CASE WHEN {c} THEN {inner} END)"
    if func == "COUNT":
        return f"SUM(CASE WHEN {c} THEN 1 ELSE 0 END)"
    raise ValueError(f"未知聚合函数: {func}")


def expand_metric(metric: MetricDef, registry: MetricRegistry) -> str:
    """把指标编译为 SQL 聚合片段。

    - additive → 条件聚合（指标 filters 包裹进 CASE WHEN）
    - ratio → SUM(num)/NULLIF(SUM(den),0) 的最终聚合层现算；禁止对率值再聚合（RateTrapError）
    """
    if metric.type != "ratio":
        func, inner = parse_aggregate(metric.expression or "")
        return agg_sql(func, inner, metric.filters)

    # ratio：分子/分母各自独立展开
    num_id = metric.numerator
    den_id = metric.denominator
    if num_id is None or den_id is None:
        raise RateTrapError(detail=f"比率指标「{metric.name_cn}」缺少分子/分母")
    num = registry.get_metric(num_id)
    den = registry.get_metric(den_id)
    num_func, num_inner = parse_aggregate(num.expression or "")
    den_func, den_inner = parse_aggregate(den.expression or "")
    num_sql = agg_sql(num_func, num_inner, num.filters)
    den_sql = agg_sql(den_func, den_inner, den.filters)
    # 强制 numeric 除法：整数/整数在 PostgreSQL 会截断为 0
    return f"({num_sql})::numeric / NULLIF(({den_sql})::numeric, 0)"


def guard_no_reaggregation(metric: MetricDef, requested_agg: str) -> None:
    """若对 ratio 指标请求了非 sum 聚合（即对率值再 AVG/SUM），抛 RateTrapError。"""
    if metric.type == "ratio" and requested_agg != "sum":
        raise RateTrapError(
            detail=f"比率指标「{metric.name_cn}」必须在最终聚合层按 分子合计/分母合计 现算，"
            f"禁止对率值再做 {requested_agg.upper()}（否则品类大小的算术平均不等于全局值）"
        )
