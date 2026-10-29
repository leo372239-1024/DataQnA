"""有效性验证：经验被使用后 hurt_count>0 即撤销（有效才持久）。"""
from app.memory.models import Lesson
from app.memory.store import MemoryStore


def test_hurt_count_revokes_lesson():
    store = MemoryStore()
    store.upsert_lesson(
        Lesson(
            id="l1", tenant_id="t1", lesson="补充别名华南", action="add_alias",
            confidence=0.9, status="admitted",
        )
    )
    # 先帮助一次
    store.record_outcome("t1", "l1", helped=True)
    lesson = store.get_lesson("t1", "l1")
    assert lesson.applied_count == 1 and lesson.helped_count == 1 and lesson.status == "admitted"

    # 再伤害一次 → 撤销
    store.record_outcome("t1", "l1", helped=False)
    lesson = store.get_lesson("t1", "l1")
    assert lesson.hurt_count == 1
    assert lesson.status == "revoked"


def test_helped_keeps_lesson_active():
    store = MemoryStore()
    store.upsert_lesson(
        Lesson(
            id="l2", tenant_id="t1", lesson="x",
            action="other", confidence=0.8, status="admitted",
        )
    )
    store.record_outcome("t1", "l2", helped=True)
    store.record_outcome("t1", "l2", helped=True)
    lesson = store.get_lesson("t1", "l2")
    assert lesson.net_effect == 2
    assert lesson.status == "admitted"
