"""RLS 注入：每次事实表扫描都带租户约束（编译期绑定 + DB RLS 双保险）。"""
import datetime as dt
from pathlib import Path

from app.core.errors import MissingSecurityContextError
from app.dsl.compiler import SecurityContext, compile_sql
from app.dsl.models import MetricRef, QueryDSL, TimeWindow
from app.semantic.registry import MetricRegistry


def _dsl() -> QueryDSL:
    return QueryDSL(
        metrics=[MetricRef(metric_id="gmv_paid", semantic_version=1)],
        time=TimeWindow(start_date=dt.date(2026, 8, 1), end_date=dt.date(2026, 9, 1)),
        semantic_version=1,
    )


def test_rls_injected_every_fact_scan():
    reg = MetricRegistry.from_yaml("app/seed/metrics/registry.yaml")
    compiled = compile_sql(_dsl(), reg, SecurityContext(tenant_id="t1"))
    # 编译期租户约束
    assert "tenant_id = $1" in compiled.sql
    # 租户是第一个绑定参数
    assert compiled.params[0] == "t1"


def test_missing_security_context_rejected():
    reg = MetricRegistry.from_yaml("app/seed/metrics/registry.yaml")
    import pytest

    with pytest.raises(MissingSecurityContextError):
        compile_sql(_dsl(), reg, SecurityContext(tenant_id=""))


def test_db_rls_policy_present_in_schema():
    """DB 层 RLS 策略（current_setting('app.tenant_id')）作为第二道防线存在。"""
    schema = Path("app/seed/schema.py").read_text(encoding="utf-8")
    assert "current_setting('app.tenant_id'" in schema or "app.tenant_id" in schema
