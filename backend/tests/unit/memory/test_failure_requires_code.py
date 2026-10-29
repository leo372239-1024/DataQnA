"""失败必须携带 9 类失败码：自由文本失败码/缺失码在模型层即被拒绝。"""
import pytest
from pydantic import ValidationError

from app.memory.failure_codes import is_valid_failure_code, validate_failure_code
from app.memory.models import Episode


def test_failure_without_code_rejected():
    with pytest.raises(ValidationError):
        Episode(id="e1", tenant_id="t1", question="x", outcome="failure", failure_code=None)


def test_failure_with_free_text_code_rejected():
    with pytest.raises(ValidationError):
        Episode(
            id="e2", tenant_id="t1", question="x",
            outcome="failure", failure_code="something went wrong",
        )


def test_success_without_code_allowed():
    ep = Episode(id="e3", tenant_id="t1", question="x", outcome="success")
    assert ep.failure_code is None


def test_all_nine_codes_valid():
    from app.memory.failure_codes import FAILURE_CODES

    assert len(FAILURE_CODES) == 9
    for code in FAILURE_CODES:
        assert is_valid_failure_code(code)
        validate_failure_code(code)
