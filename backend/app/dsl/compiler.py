"""确定性编译器：QueryDSL → 参数化 PostgreSQL SQL。

8 步固定顺序：resolve → rate normalize → from/join → RLS 注入 → 分区裁剪
→ render → compare → fingerprint。
所有用户派生值（时间、维度值、limit）都是绑定参数，零字符串插值。
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from typing import Any

from app.core.errors import MissingSecurityContextError
from app.dsl.models import QueryDSL
from app.dsl.rate import expand_metric, guard_no_reaggregation
from app.semantic.models import DimensionDef
from app.semantic.registry import MetricRegistry

_MAIN_TABLE = "analytics.fact_order"
_MAIN_ALIAS = "o"


@dataclass
class SecurityContext:
    tenant_id: str
    allowed_region_ids: list[int] | None = None  # None = 不限


@dataclass
class CompiledQuery:
    sql: str
    params: list[Any]
    dsl_fingerprint: str
    sql_fingerprint: str
    metric_ids: list[str] = field(default_factory=list)
    dimension_ids: list[str] = field(default_factory=list)
    scanned_tables: list[str] = field(default_factory=list)


def _qualified_col(dim: DimensionDef) -> str:
    """维度值列带 join 别名。"""
    if "." in dim.value_column:
        return dim.value_column
    m = re.search(r"JOIN\s+\S+\s+(\w+)", dim.join_sql)
    alias = m.group(1) if m else _MAIN_ALIAS
    return f"{alias}.{dim.value_column}"


def _canonicalize_value(dim: DimensionDef, value: str | float) -> str:
    """把用户给的维度值归一化为规范值（值别名 → 规范值），其余原样作为绑定参数。"""
    vv = str(value)
    for canon, aliases in (dim.value_aliases or {}).items():
        if vv in aliases:
            return canon
    return vv


def _fingerprint(obj: Any) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()[:16]


def _compile_window(
    dsl: QueryDSL, registry: MetricRegistry, ctx: SecurityContext,
) -> tuple[str, list[Any], list[str], list[str]]:
    """编译单个时间窗口（不含 compare）。返回 (sql, params, metric_ids, dimension_ids)。"""
    # 1. resolve
    metric_defs = [registry.get_metric(m.metric_id) for m in dsl.metrics]
    dim_defs = [registry.get_dimension(d.dimension_id) for d in dsl.dimensions]

    # 2. rate normalize + 反率值再聚合
    metric_sqls: list[str] = []
    for mdef, ref in zip(metric_defs, dsl.metrics, strict=False):
        guard_no_reaggregation(mdef, ref.aggregation)
        metric_sqls.append(expand_metric(mdef, registry))

    # 3. from / join（去重；join 表名补 analytics schema 前缀）
    joins: list[str] = []
    seen_joins: set[str] = set()
    for d in dim_defs:
        join_sql = re.sub(r"JOIN\s+(\w+)", r"JOIN analytics.\1", d.join_sql)
        if join_sql not in seen_joins:
            joins.append(join_sql)
            seen_joins.add(join_sql)
    from_clause = f"FROM {_MAIN_TABLE} {_MAIN_ALIAS} " + " ".join(joins)

    # 4. RLS 注入
    if not ctx.tenant_id:
        raise MissingSecurityContextError("编译缺少租户上下文（SecurityContext.tenant_id）")
    params: list[Any] = [ctx.tenant_id]
    where = [f"{_MAIN_ALIAS}.tenant_id = $1"]
    if ctx.allowed_region_ids is not None:
        params.append(ctx.allowed_region_ids)
        where.append(f"{_MAIN_ALIAS}.region_id = ANY(${len(params)})")

    # 4.5 维度值过滤（全绑定参数 + 值别名归一化；用户派生值绝不进 SQL 文本）
    for f in dsl.filters:
        dim = registry.get_dimension(f.dimension_id)
        col = _qualified_col(dim)
        values = [_canonicalize_value(dim, v) for v in f.values]
        if f.operator == "in":
            ph = ", ".join(f"${len(params) + i + 1}" for i in range(len(values)))
            params.extend(values)
            where.append(f"{col} IN ({ph})")
        elif f.operator == "eq":
            params.append(values[0])
            where.append(f"{col} = ${len(params)}")
        elif f.operator == "gte":
            params.append(values[0])
            where.append(f"{col} >= ${len(params)}")
        elif f.operator == "lte":
            params.append(values[0])
            where.append(f"{col} <= ${len(params)}")
        elif f.operator == "between":
            params.extend(values[:2])
            where.append(f"{col} >= ${len(params) - 1} AND {col} <= ${len(params)}")

    # 5. 分区裁剪（时间列取第一个指标的 default_time_col）
    time_col = metric_defs[0].default_time_col or f"{_MAIN_ALIAS}.paid_at"
    params.append(dsl.time.start_date)
    params.append(dsl.time.end_date)
    where.append(f"{time_col} >= ${len(params) - 1}")
    where.append(f"{time_col} < ${len(params)}")

    # 6. render SELECT
    selects: list[str] = []
    for d in dim_defs:
        selects.append(f"{_qualified_col(d)} AS {d.id}")
    for i, msql in enumerate(metric_sqls):
        selects.append(f"{msql} AS m{i}")

    sql = f"SELECT {', '.join(selects)} {from_clause} WHERE {' AND '.join(where)}"
    if dim_defs:
        sql += " GROUP BY " + ", ".join(_qualified_col(d) for d in dim_defs)

    # ORDER BY / LIMIT
    order_clauses: list[str] = []
    for o in dsl.order:
        if o.target.startswith("m") and o.target[1:].isdigit():
            order_clauses.append(f"m{int(o.target[1:])} {o.direction.upper()}")
        else:
            order_clauses.append(f"{o.target} {o.direction.upper()}")
    if order_clauses:
        sql += " ORDER BY " + ", ".join(order_clauses)
    if dsl.limit is not None:
        params.append(dsl.limit)
        sql += f" LIMIT ${len(params)}"

    return sql, params, [m.id for m in metric_defs], [d.id for d in dim_defs]


def compile_sql(dsl: QueryDSL, registry: MetricRegistry, ctx: SecurityContext) -> CompiledQuery:
    """编译 QueryDSL → CompiledQuery（单时间窗口）。

    compare 语义由编排层（planner 拆 q1/q2 两个子目标）负责，编译器保持单窗口纯粹性。
    """
    sql, params, mids, dims = _compile_window(dsl, registry, ctx)

    dsl_fp = _fingerprint(dsl.model_dump(mode="json"))
    sql_fp = _fingerprint(sql)
    return CompiledQuery(
        sql=sql, params=params, dsl_fingerprint=dsl_fp, sql_fingerprint=sql_fp,
        metric_ids=mids, dimension_ids=dims, scanned_tables=[_MAIN_TABLE],
    )
