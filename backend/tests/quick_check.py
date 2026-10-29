"""端到端快速验证：registry → linker → time → DSL → compile → execute → 率值陷阱。"""
import asyncio
import sys

sys.path.insert(0, ".")

from datetime import date

from app.dsl.compiler import SecurityContext, compile_sql
from app.dsl.models import DimensionRef, MetricRef, QueryDSL, TimeWindow
from app.query.gateway import QueryGateway
from app.semantic.linker import link_metric
from app.semantic.registry import MetricRegistry
from app.semantic.time_resolver import resolve


async def main() -> None:
    reg = MetricRegistry.from_yaml("app/seed/metrics/registry.yaml")
    print(f"registry: {len(reg.metrics)} metrics, "
          f"{len(reg.dimensions)} dims, sv={reg.semantic_version}")

    # 1. 实体链接
    for mention in ["GMV", "退款率", "客单价", "不存在的指标XYZ"]:
        link = link_metric(reg, mention)
        print(f"link('{mention}') -> {link.status} "
              f"{link.metric.id if link.metric else ''} (conf={link.confidence})")

    # 2. 时间解析
    for expr in ["上月", "近30天", "去年同期", "2026年9月"]:
        t = resolve(expr)
        print(f"time('{expr}') -> {t}")

    # 3. L1 单指标：上月 GMV
    t = resolve("上月")
    dsl = QueryDSL(
        metrics=[MetricRef(metric_id="gmv_paid", semantic_version=reg.semantic_version)],
        time=TimeWindow(start_date=t.start_date, end_date=t.end_date),
        semantic_version=reg.semantic_version,
    )
    ctx = SecurityContext(tenant_id="t1")
    compiled = compile_sql(dsl, reg, ctx)
    print("\nL1 SQL:\n", compiled.sql, "\nparams:", compiled.params)

    gw = QueryGateway()
    result = await gw.execute(compiled, ctx, reg.semantic_version, "roles_hash")
    print("L1 上月 GMV =", result.rows)

    # 4. 率值陷阱验证：各品类退款率的算术平均 vs 全局退款率
    rate_dsl = QueryDSL(
        metrics=[MetricRef(metric_id="refund_rate", semantic_version=reg.semantic_version)],
        dimensions=[DimensionRef(dimension_id="category")],
        time=TimeWindow(start_date=date(2026, 1, 1), end_date=date(2026, 10, 1)),
        semantic_version=reg.semantic_version,
    )
    compiled2 = compile_sql(rate_dsl, reg, ctx)
    r2 = await gw.execute(compiled2, ctx, reg.semantic_version, "rh")
    by_cat = [(r["category"], round(float(r["m0"]), 6)) for r in r2.rows]
    print("\n各品类退款率:", by_cat)
    if by_cat:
        avg = sum(x[1] for x in by_cat) / len(by_cat)
        print(f"各品类算术平均 = {avg:.6f}")

    # 全局退款率（无维度）
    global_dsl = QueryDSL(
        metrics=[MetricRef(metric_id="refund_rate", semantic_version=reg.semantic_version)],
        time=TimeWindow(start_date=date(2026, 1, 1), end_date=date(2026, 10, 1)),
        semantic_version=reg.semantic_version,
    )
    compiled3 = compile_sql(global_dsl, reg, ctx)
    r3 = await gw.execute(compiled3, ctx, reg.semantic_version, "rh")
    print("全局退款率 =", [round(float(x["m0"]), 6) for x in r3.rows])


asyncio.run(main())
