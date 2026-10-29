"""口径只来自注册表，绝不来自 LLM：指标定义文本是 registry 的单一真相源。"""
import datetime as dt

from app.agent.orchestrator import Orchestrator
from app.agent.state import AgentState, IntentFrame, SubgoalResult
from app.dsl.compiler import SecurityContext
from app.semantic.registry import MetricRegistry


def test_all_metrics_have_registry_caliber():
    reg = MetricRegistry.from_yaml("app/seed/metrics/registry.yaml")
    for m in reg.metrics:
        assert m.caliber_cn, f"指标 {m.id} 缺少口径"


def test_answer_caliber_sourced_from_registry():
    reg = MetricRegistry.from_yaml("app/seed/metrics/registry.yaml")
    # 构造一个不需要 DB 的 Orchestrator（_synthesize 只读 registry + state）
    orch = Orchestrator(reg, None)  # type: ignore[arg-type]
    state = AgentState(question="上月GMV", tenant_id="t1")
    state.intent = IntentFrame(
        level="L1", metric_ids=["gmv_paid"],
        start_date=dt.date(2026, 8, 1), end_date=dt.date(2026, 9, 1),
    )
    state.results["q1"] = SubgoalResult(subgoal_id="q1", status="ok", rows=[{"m0": 1.0}])

    env = orch._synthesize(state, SecurityContext(tenant_id="t1"))
    metric = reg.get_metric("gmv_paid")
    # 口径必须来自注册表，与 LLM 无关
    assert env.caliber == metric.caliber_cn
    assert "已支付订单金额" in env.caliber
