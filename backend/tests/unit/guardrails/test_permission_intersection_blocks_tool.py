"""权限交集：越权资产对无权调用者不可见。"""
from app.guardrails.permissions import (
    assert_metric_visible,
    effective_scope,
    intersect_roles,
)
from app.routing.models import Asset
from app.semantic.models import MetricDef


def _asset(permissions: list[str]) -> Asset:
    return Asset(
        id="export_report", kind="skill", name="导出", description="导出",
        capability="导出报告", permissions=permissions, risk="high",
    )


def test_permission_intersection_blocks_tool():
    asset = _asset(["analyst"])
    assert not intersect_roles(set(), asset)
    assert not intersect_roles({"viewer"}, asset)
    assert intersect_roles({"analyst"}, asset)


def test_empty_permissions_public():
    asset = _asset([])
    assert intersect_roles(set(), asset)


def test_effective_scope_intersects_roles_and_permissions():
    scope = effective_scope({"analyst", "viewer"}, ["analyst", "admin"], ["fact_order"])
    assert scope == ["analyst"]


def test_metric_visibility_by_table_scope():
    metric = MetricDef(
        id="gmv", name_cn="GMV", type="additive", expression="SUM(1)",
        source_tables=["fact_order"], caliber_cn="x",
    )
    assert assert_metric_visible(metric, {"fact_order"})
    assert not assert_metric_visible(metric, {"dim_user"})
