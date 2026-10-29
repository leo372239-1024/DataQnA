"""负记忆：已记录的「请求 X 不应路由到 Y」在 Stage 3 施加硬惩罚。"""
from app.routing.registry import AssetRegistry
from app.routing.router import Router


async def test_negative_memory_penalizes(registry: AssetRegistry):
    router = Router(registry)
    # 未记录负记忆时，「为什么退款率上升」应命中归因分析
    before = await router.route("为什么退款率上升了", set())
    assert before.asset_id == "attribution_analysis"

    # 记录负记忆：该请求不应路由到 attribution_analysis
    router.record_negative("为什么退款率上升了", "attribution_analysis", penalty=0.8)

    after = await router.route("为什么退款率上升了", set())
    # 惩罚后要么不再命中原资产，要么降级为澄清；绝不能带着高置信命中被惩罚资产
    assert after.asset_id != "attribution_analysis" or not after.resolved


async def test_negative_memory_penalty_value(registry: AssetRegistry):
    router = Router(registry)
    router.record_negative("x", "sql_query", penalty=0.5)
    assert router._penalty("x", "sql_query") == 0.5
    assert router._penalty("other", "sql_query") == 0.0
    assert router._penalty("x", "other_asset") == 0.0
