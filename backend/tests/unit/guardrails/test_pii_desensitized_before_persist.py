"""PII 脱敏：在持久化源头脱敏，递归覆盖嵌套结构。"""
from app.guardrails.desensitize import desensitize


def test_email_phone_idcard_desensitized():
    s = "联系 alice@example.com 或 13800138000，身份证 110101199003078515"
    out = desensitize(s)
    assert "alice@example.com" not in out
    assert "13800138000" not in out
    assert "110101199003078515" not in out
    assert "[EMAIL]" in out
    assert "[PHONE]" in out
    assert "[IDCARD]" in out


def test_nested_structure_desensitized():
    payload = {
        "user": {"name": "张三", "email": "bob@example.com"},
        "rows": [{"phone": "13900139000"}],
    }
    out = desensitize(payload)
    assert out["user"]["email"] == "[EMAIL]"
    assert out["rows"][0]["phone"] == "[PHONE]"
    assert out["user"]["name"] == "张三"  # 非 PII 保留


def test_non_string_passthrough():
    assert desensitize(42) == 42
    assert desensitize(3.14) == 3.14
    assert desensitize(None) is None
