"""审计日志：每次工具调用/查询都落一条（含成功），参数脱敏后持久化。"""
from app.guardrails.audit import AuditEntry, AuditLogger


def test_audit_log_written_per_call():
    logger = AuditLogger()
    logger.record(AuditEntry(tenant_id="t1", actor="u1", action="sql_query", params={"q": "GMV"}))
    logger.record(
        AuditEntry(tenant_id="t1", actor="u1", action="export_report", result_code="DENIED")
    )
    assert len(logger.records("t1")) == 2


def test_audit_includes_success_not_just_failure():
    logger = AuditLogger()
    logger.record(AuditEntry(tenant_id="t1", actor="u1", action="sql_query", result_code="OK"))
    assert logger.records()[0]["result_code"] == "OK"


def test_audit_pii_desensitized_before_persist():
    logger = AuditLogger()
    logger.record(
        AuditEntry(
            tenant_id="t1", actor="u1", action="email_send",
            params={"to": "alice@example.com", "phone": "13800138000"},
        )
    )
    persisted = logger.records("t1")[0]["params"]
    assert "alice@example.com" not in str(persisted)
    assert "13800138000" not in str(persisted)
    assert "[EMAIL]" in str(persisted)
    assert "[PHONE]" in str(persisted)
