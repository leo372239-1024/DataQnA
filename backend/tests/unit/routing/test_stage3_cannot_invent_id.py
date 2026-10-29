"""Stage 3：重排器输出被严格约束在候选 id 内（禁止凭空发明 id）。"""
from app.routing.rerank import _validate_rerank_output


def test_rerank_output_constrained_to_candidates():
    candidate_ids = ["sql_query", "compare_analysis", "chart_render"]
    validate = _validate_rerank_output(candidate_ids)
    # 合法输出
    out = validate({"choice": "compare_analysis", "confidence": 0.9})
    assert out["choice"] == "compare_analysis"
    assert out["confidence"] == 0.9


def test_rerank_rejects_invented_id():
    candidate_ids = ["sql_query", "compare_analysis"]
    validate = _validate_rerank_output(candidate_ids)
    import pytest

    with pytest.raises(ValueError):
        validate({"choice": "not_a_real_asset", "confidence": 0.9})


def test_rerank_rejects_non_object():
    validate = _validate_rerank_output(["sql_query"])
    import pytest

    with pytest.raises(ValueError):
        validate('"just a string"')


def test_rerank_clamps_confidence():
    validate = _validate_rerank_output(["sql_query"])
    out = validate({"choice": "sql_query", "confidence": 5.0})
    assert out["confidence"] == 1.0
