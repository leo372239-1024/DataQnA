"""反思隐私边界：Episode 不携带原始工具 payload，反思只读摘要与失败码。"""
from app.memory.models import Episode
from app.memory.reflection import ReflectionEngine
from app.memory.store import MemoryStore


async def test_episode_has_no_raw_payload_field():
    ep = Episode(id="e1", tenant_id="t1", question="x", outcome="success")
    assert not hasattr(ep, "payload")
    assert not hasattr(ep, "raw")
    assert not hasattr(ep, "tool_output")


async def test_reflection_reads_only_summary_and_code():
    """反思引擎只依赖 subgoal_summary + failure_code，可从摘要推断作用对象。"""
    store = MemoryStore()
    eng = ReflectionEngine(store, auto_admit=True)
    # 摘要中带 asset_id，但没有任何原始数据行
    ep = Episode(
        id="e2", tenant_id="t1", question="x", outcome="failure", failure_code="TOOL_MISUSE",
        subgoal_summary=[{"subgoal_id": "q1", "status": "failed", "asset_id": "sql_query"}],
    )
    lessons = await eng.reflect(ep)
    assert lessons[0].applies_to == "sql_query"
    # 推断只读摘要，不访问任何原始 payload（模型层根本不存在该字段）
