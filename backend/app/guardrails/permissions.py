"""权限交集（越权防线）：effective_scope = caller.roles ∩ tool.permissions ∩ metric.table_scope。

agent 以用户身份运行（身份透传），永不用服务超管身份。最高权限操作也只是受 RLS 约束的只读查询。
"""
from __future__ import annotations

from app.routing.models import Asset
from app.semantic.models import MetricDef


def intersect_roles(caller_roles: set[str], asset: Asset) -> bool:
    """资产可见性：caller_roles 必须覆盖资产全部权限要求。空权限 = 人人可用。"""
    if not asset.permissions:
        return True
    return set(asset.permissions) <= caller_roles


def effective_scope(
    caller_roles: set[str],
    asset_permissions: list[str],
    table_scope: list[str],
) -> list[str]:
    """计算有效范围：角色 ∩ 资产权限 ∩ 表范围。"""
    roles = set(caller_roles)
    perms = set(asset_permissions)
    tables = set(table_scope)
    return sorted(roles & perms) if perms else sorted(roles & tables) if tables else sorted(roles)


def assert_metric_visible(metric: MetricDef, visible_table_scope: set[str]) -> bool:
    """指标可见性：指标所有源表都在调用者可访问的表范围内。"""
    if not visible_table_scope:
        return True  # 空范围表示不限（已由 RLS 兜底）
    return all(t in visible_table_scope for t in metric.source_tables)
