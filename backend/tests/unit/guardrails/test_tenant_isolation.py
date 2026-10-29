"""多租户隔离：审计/记忆/缓存都按租户键控，无跨租户缓存。"""
from app.guardrails.audit import AuditEntry, AuditLogger
from app.memory.models import Episode
from app.memory.store import MemoryStore


def test_audit_tenant_isolation():
    logger = AuditLogger()
    logger.record(AuditEntry(tenant_id="A", actor="u", action="sql_query"))
    logger.record(AuditEntry(tenant_id="B", actor="u", action="sql_query"))
    assert len(logger.records("A")) == 1
    assert logger.records("A")[0]["tenant_id"] == "A"
    assert len(logger.records("B")) == 1


def test_memory_tenant_isolation_via_guardrails():
    store = MemoryStore()
    store.add_episode(Episode(id="a1", tenant_id="A", question="x", outcome="success"))
    assert [e.id for e in store.episodes("B")] == []


def test_cache_key_includes_tenant_and_roles():
    """缓存键含 tenant_id + roles_hash，杜绝跨租户/跨角色缓存命中。"""
    from app.dsl.compiler import CompiledQuery, SecurityContext
    from app.query.gateway import _cache_key

    compiled = CompiledQuery(sql="", params=[], dsl_fingerprint="fp", sql_fingerprint="sf")
    k1 = _cache_key(compiled, SecurityContext(tenant_id="A"), 1, "r1")
    k2 = _cache_key(compiled, SecurityContext(tenant_id="B"), 1, "r1")
    k3 = _cache_key(compiled, SecurityContext(tenant_id="A"), 1, "r2")
    assert k1 != k2
    assert k1 != k3
