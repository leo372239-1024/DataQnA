"""四道校验：静态 / 语义 / 成本 / 结果。"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.dsl.compiler import CompiledQuery, SecurityContext
from app.dsl.models import QueryDSL
from app.semantic.registry import TABLE_WHITELIST, MetricRegistry

MAX_SCAN_BYTES_HINT = 5 * 1024**3  # 5GB 提示阈值（MVP 简化）
MAX_RESULT_ROWS = 10_000


@dataclass
class Violation:
    gate: str  # static | semantic | cost | result
    failure_code: str
    detail: str
    blocking: bool = True


def check_static(dsl: QueryDSL, registry: MetricRegistry, ctx: SecurityContext) -> list[Violation]:
    v: list[Violation] = []
    for m in dsl.metrics:
        try:
            registry.get_metric(m.metric_id)
        except KeyError:
            v.append(Violation("static", "STATIC_VIOLATION", f"指标 {m.metric_id} 未注册"))
    for d in dsl.dimensions:
        try:
            registry.get_dimension(d.dimension_id)
        except KeyError:
            v.append(Violation("static", "STATIC_VIOLATION", f"维度 {d.dimension_id} 未注册"))
    # 表白名单（维度 join 的目标表）
    for d in dsl.dimensions:
        dim = registry.get_dimension(d.dimension_id)
        if dim.table not in TABLE_WHITELIST:
            v.append(Violation("static", "STATIC_VIOLATION",
                               f"维度 {d.dimension_id} 表 {dim.table} 未白名单"))
    return v


def check_semantic(
    dsl: QueryDSL, registry: MetricRegistry, ctx: SecurityContext,
) -> list[Violation]:
    v: list[Violation] = []
    # compare 需要稳定时间锚（MVP：必须有 start/end，已由 model 保证）
    # metric × dimension 可组合性：维度 join 必须能接到主表（join_sql 非空即可）
    for d in dsl.dimensions:
        dim = registry.get_dimension(d.dimension_id)
        if not dim.join_sql:
            v.append(Violation("semantic", "SEMANTIC_VIOLATION",
                               f"维度 {d.dimension_id} 无 join 路径，不可与指标组合"))
    return v


def check_cost(dsl: QueryDSL, compiled: CompiledQuery, ctx: SecurityContext) -> list[Violation]:
    v: list[Violation] = []
    # MVP：结构性成本校验——必须带时间 bound（模型已保证），limit 保护
    if dsl.limit is None and not dsl.dimensions:
        # 无维度且无 limit 的标量查询，天然单行，OK
        pass
    if dsl.limit is not None and dsl.limit > MAX_RESULT_ROWS:
        v.append(Violation("cost", "COST_VIOLATION",
                           f"limit {dsl.limit} 超过最大行数 {MAX_RESULT_ROWS}", blocking=False))
    return v


def check_result(rows: list[dict[str, Any]], dsl: QueryDSL) -> list[Violation]:
    v: list[Violation] = []
    if not rows:
        v.append(Violation("result", "EMPTY_RESULT",
                           "查询无数据：可能时间范围过窄或无匹配条件", blocking=False))
    # 负值检测（金额/数量不应为负）
    for i, _ in enumerate(dsl.metrics):
        key = f"m{i}"
        for r in rows:
            val = r.get(key)
            if isinstance(val, (int, float)) and val < 0:
                v.append(Violation("result", "RESULT_ANOMALY",
                                   f"指标 {key} 出现负值 {val}，请检查口径", blocking=False))
                break
    return v
