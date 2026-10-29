"""注入防御：用户派生值（维度值/时间/租户）全部绑定参数，绝不进入 SQL 文本。"""
import datetime as dt

from app.dsl.compiler import SecurityContext, compile_sql
from app.dsl.models import Filter, MetricRef, QueryDSL, TimeWindow
from app.semantic.registry import MetricRegistry

PAYLOADS = [
    "'; DROP TABLE users; --",
    "1) OR 1=1 --",
    "${jndi:ldap://evil}",
    "x' UNION SELECT * FROM secrets --",
]


def _dsl_with_filter(values: list) -> QueryDSL:
    return QueryDSL(
        metrics=[MetricRef(metric_id="gmv_paid", semantic_version=1)],
        dimensions=[],
        time=TimeWindow(start_date=dt.date(2026, 8, 1), end_date=dt.date(2026, 9, 1)),
        filters=[Filter(dimension_id="region", operator="in", values=values)],
        semantic_version=1,
    )


def test_injection_payloads_are_bound():
    reg = MetricRegistry.from_yaml("app/seed/metrics/registry.yaml")
    ctx = SecurityContext(tenant_id="t1")
    dsl = _dsl_with_filter(PAYLOADS)
    compiled = compile_sql(dsl, reg, ctx)

    # 每个 payload 都必须是绑定参数，绝不拼进 SQL 文本
    for p in PAYLOADS:
        assert p not in compiled.sql
        assert p in compiled.params
    # SQL 里出现的是占位符，不是字面量
    assert "DROP TABLE" not in compiled.sql
    assert "UNION SELECT" not in compiled.sql


def test_all_user_derived_values_bound():
    reg = MetricRegistry.from_yaml("app/seed/metrics/registry.yaml")
    ctx = SecurityContext(tenant_id="t1")
    dsl = QueryDSL(
        metrics=[MetricRef(metric_id="gmv_paid", semantic_version=1)],
        time=TimeWindow(start_date=dt.date(2026, 8, 1), end_date=dt.date(2026, 9, 1)),
        semantic_version=1,
    )
    compiled = compile_sql(dsl, reg, ctx)
    # 租户 + 时间都是绑定参数
    assert "t1" in compiled.params
    assert dt.date(2026, 8, 1) in compiled.params
    assert dt.date(2026, 9, 1) in compiled.params


def test_value_alias_canonicalized_but_bound():
    reg = MetricRegistry.from_yaml("app/seed/metrics/registry.yaml")
    ctx = SecurityContext(tenant_id="t1")
    dsl = _dsl_with_filter(["华南大区", "华东"])
    compiled = compile_sql(dsl, reg, ctx)
    # 值别名归一化后仍是绑定参数，不是 SQL 字面量
    assert "华南大区" not in compiled.sql
    assert "华南" in compiled.params  # 归一化为规范值
