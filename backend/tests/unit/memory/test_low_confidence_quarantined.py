"""入池门槛：低置信经验进隔离区，绝不自动应用。"""
from app.memory.models import ADMIT_THRESHOLD, Episode
from app.memory.reflection import ReflectionEngine
from app.memory.store import MemoryStore


async def test_low_confidence_quarantined():
    store = MemoryStore()
    # 非自动应用模式：即便置信度达标也只进隔离区等待人工
    eng = ReflectionEngine(store, auto_admit=False)
    ep = Episode(
        id="e1", tenant_id="t1", question="x", outcome="failure", failure_code="METRIC_AMBIG"
    )
    lessons = await eng.reflect(ep)
    assert lessons[0].confidence < ADMIT_THRESHOLD
    assert lessons[0].status == "quarantined"


async def test_high_confidence_auto_admit_only_when_enabled():
    store = MemoryStore()
    eng_manual = ReflectionEngine(store, auto_admit=False)
    ep = Episode(
        id="e2", tenant_id="t1", question="x", outcome="failure", failure_code="NO_MATCH"
    )
    lesson = (await eng_manual.reflect(ep))[0]
    assert lesson.confidence >= ADMIT_THRESHOLD
    assert lesson.status == "quarantined"  # 未开 auto_admit，仍隔离等待人工

    store2 = MemoryStore()
    eng_auto = ReflectionEngine(store2, auto_admit=True)
    lesson2 = (await eng_auto.reflect(ep))[0]
    assert lesson2.status == "admitted"


async def test_lesson_carries_evidence():
    store = MemoryStore()
    eng = ReflectionEngine(store, auto_admit=True)
    ep = Episode(
        id="e3", tenant_id="t1", question="x", outcome="failure", failure_code="NO_MATCH"
    )
    lesson = (await eng.reflect(ep))[0]
    assert lesson.evidence_episode_id == "e3"
