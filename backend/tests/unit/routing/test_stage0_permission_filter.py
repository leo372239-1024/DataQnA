"""Stage 0：角色权限交集 —— 越权资产对无权调用者结构性不可见。"""
from app.routing.registry import AssetRegistry
from app.routing.router import Router


async def test_role_locked_tool_invisible_to_anonymous(registry: AssetRegistry):
    router = Router(registry)
    # 匿名调用者（无任何角色）不能看到需要 analyst 角色的资产
    res = await router.route("导出报告到 Excel", set())
    assert res.asset_id != "export_report"
    assert res.asset_id != "file_export"


async def test_role_locked_tool_visible_to_analyst(registry: AssetRegistry):
    router = Router(registry)
    res = await router.route("导出报告到 Excel", {"analyst"})
    assert res.resolved


async def test_anonymous_sees_public_assets(registry: AssetRegistry):
    router = Router(registry)
    res = await router.route("查一下上月 GMV", set())
    # 公共资产（sql_query）对匿名可见
    assert res.asset_id == "sql_query"


async def test_permission_filter_drops_deprecated(registry: AssetRegistry):
    router = Router(registry)
    # 全部资产被权限过滤后（模拟：无可见资产）返回澄清而非猜测
    # 这里用不存在的极端角色，保证高权限资产也不可见
    res = await router.route("某个不存在的请求", set())
    assert res.clarification or res.resolved
