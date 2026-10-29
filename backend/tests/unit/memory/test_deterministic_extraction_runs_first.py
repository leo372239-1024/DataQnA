"""确定性抽取先于 LLM：候选来自失败码信号，成功且无信号的 episode 不产经验。"""
from app.memory.models import Episode
from app.memory.reflection import ReflectionEngine
from app.memory.store import MemoryStore


async def test_success_episode_produces_no_lesson():
    store = MemoryStore()
    eng = ReflectionEngine(store)
    ep = Episode(
        id="e1", tenant_id="t1", question="上月GMV", outcome="success",
        subgoal_summary=[{"subgoal_id": "q1", "status": "ok"}],
    )
    lessons = await eng.reflect(ep)
    assert lessons == []


async def test_failure_extracts_from_failure_code():
    store = MemoryStore()
    eng = ReflectionEngine(store)
    ep = Episode(
        id="e2", tenant_id="t1", question="华南退货率", outcome="failure",
        failure_code="NO_MATCH",
        subgoal_summary=[{"subgoal_id": "q1", "status": "failed", "failure_code": "NO_MATCH"}],
    )
    lessons = await eng.reflect(ep)
    assert len(lessons) == 1
    assert lessons[0].action == "add_alias"


async def test_extraction_does_not_need_llm():
    """抽取阶段纯确定性：不依赖网关/网络。"""
    store = MemoryStore()
    eng = ReflectionEngine(store)
    ep = Episode(
        id="e3", tenant_id="t1", question="x", outcome="failure", failure_code="TOOL_MISUSE"
    )
    lessons = await eng.reflect(ep)
    assert lessons[0].evidence_episode_id == "e3"
    assert lessons[0].confidence == 0.70
