"""Stage 1：别名精确命中短路 —— 常见别名永远不触达向量召回。"""
from app.routing.registry import AssetRegistry
from app.routing.router import Router


async def test_alias_short_circuit(registry: AssetRegistry):
    router = Router(registry)
    res = await router.route("环比变化是多少", set())
    assert res.stage == "alias"
    assert res.asset_id == "compare_analysis"
    assert res.confidence == 0.95


async def test_longest_alias_wins(registry: AssetRegistry):
    """「归因」比「因」更长，且「归因分析」资产有别名『归因』——不能误命中其他含『因』的资产。"""
    router = Router(registry)
    res = await router.route("为什么退款率上升了", set())
    assert res.asset_id == "attribution_analysis"


async def test_exact_name_match(registry: AssetRegistry):
    router = Router(registry)
    res = await router.route("问数查询", set())
    assert res.stage == "alias"
    assert res.asset_id == "sql_query"
