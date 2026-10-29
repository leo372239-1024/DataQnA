"""歧义：候选得分接近时返回澄清，而非猜测。"""
from app.routing.models import Asset
from app.routing.registry import AssetRegistry
from app.routing.rerank import Reranker
from app.routing.router import Router


def _near_tie_assets() -> list[Asset]:
    return [
        Asset(
            id="sql_query_v1", kind="tool", name="查询订单金额",
            description="查询订单金额", aliases=[], domains=["sql"],
            capability="查询订单支付金额数据返回结果集",
        ),
        Asset(
            id="sql_query_v2", kind="tool", name="汇总订单金额",
            description="汇总订单金额", aliases=[], domains=["sql"],
            capability="查询订单支付金额数据并汇总统计",
        ),
    ]


async def test_reranker_returns_none_on_near_tie():
    assets = _near_tie_assets()
    reranker = Reranker(margin=0.12)
    choice, conf = await reranker.rerank("查询订单支付金额数据", assets)
    assert choice is None  # 两个候选太接近 → 澄清
    assert conf >= 0.0


async def test_router_returns_clarification_on_ambiguity():
    registry = AssetRegistry(_near_tie_assets())
    router = Router(registry, margin=0.12)
    res = await router.route("查询订单支付金额数据", set())
    assert not res.resolved
    assert res.clarification
    assert res.candidates  # 给出候选供用户确认


async def test_router_resolves_clear_winner():
    assets = [
        Asset(
            id="sql_query", kind="tool", name="查询数据",
            description="查询数据", aliases=[], domains=["sql"],
            capability="查询订单金额数据返回结果集",
        ),
        Asset(
            id="chart_render", kind="tool", name="渲染图表",
            description="渲染图表", aliases=[], domains=["chart"],
            capability="把结果渲染为柱状图折线图",
        ),
    ]
    registry = AssetRegistry(assets)
    router = Router(registry, margin=0.12)
    res = await router.route("查询订单金额数据", set())
    assert res.resolved
    assert res.asset_id == "sql_query"
