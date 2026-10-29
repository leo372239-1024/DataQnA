"""租户隔离：A 的记忆对 B 不可读（RLS 语义的结构性实现）。"""
from app.memory.models import Episode, SemanticMemory
from app.memory.store import MemoryStore


def test_episode_tenant_isolation():
    store = MemoryStore()
    store.add_episode(Episode(id="a1", tenant_id="A", question="x", outcome="success"))
    store.add_episode(Episode(id="b1", tenant_id="B", question="y", outcome="success"))
    assert [e.id for e in store.episodes("A")] == ["a1"]
    assert [e.id for e in store.episodes("B")] == ["b1"]


def test_semantic_search_tenant_isolation():
    store = MemoryStore()
    store.add_semantic(SemanticMemory(
        id="s1", tenant_id="A", content="华南=广东+广西+海南", status="admitted"
    ))
    store.add_semantic(SemanticMemory(
        id="s2", tenant_id="B", content="华东=上海+江苏+浙江", status="admitted"
    ))
    hits_a = store.semantic_search("A", "华南 大区")
    hits_b = store.semantic_search("B", "华南 大区")
    assert all(m.tenant_id == "A" for m, _ in hits_a)
    assert all(m.tenant_id == "B" for m, _ in hits_b)


def test_lesson_tenant_isolation():
    from app.memory.models import Lesson

    store = MemoryStore()
    store.upsert_lesson(Lesson(id="l1", tenant_id="A", lesson="x"))
    assert store.get_lesson("B", "l1") is None
    assert store.get_lesson("A", "l1") is not None
