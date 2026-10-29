"""语义层 API 契约测试。"""
from __future__ import annotations

from fastapi.testclient import TestClient


def test_health(client: TestClient) -> None:
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["app"] == "DataQnA"


def test_meta_reports_semantic_version(client: TestClient) -> None:
    r = client.get("/api/v1/meta")
    body = r.json()
    assert r.status_code == 200
    assert body["semantic_version"] >= 1
    assert body["metric_count"] >= 20
    assert body["dimension_count"] >= 8
    assert body["snapshot_date"] == "2026-09-30"


def test_list_metrics_paginated(client: TestClient) -> None:
    r = client.get("/api/v1/semantic/metrics", params={"page": 1, "page_size": 5})
    body = r.json()
    assert r.status_code == 200
    assert body["page"] == 1
    assert body["page_size"] == 5
    assert body["total"] >= 20
    assert len(body["items"]) == 5
    # 稳定排序：按 id 升序
    ids = [m["id"] for m in body["items"]]
    assert ids == sorted(ids)


def test_filter_metrics_by_type(client: TestClient) -> None:
    r = client.get("/api/v1/semantic/metrics", params={"type": "ratio"})
    body = r.json()
    assert r.status_code == 200
    assert all(m["type"] == "ratio" for m in body["items"])
    assert body["total"] >= 5  # 至少埋入 5 个 ratio 类指标


def test_list_dimensions(client: TestClient) -> None:
    r = client.get("/api/v1/semantic/dimensions")
    body = r.json()
    assert r.status_code == 200
    assert body["total"] >= 8
    assert all("hierarchy" in d for d in body["items"])


def test_metric_detail_with_lineage(client: TestClient) -> None:
    r = client.get("/api/v1/semantic/metrics/refund_rate")
    body = r.json()
    assert r.status_code == 200
    assert body["type"] == "ratio"
    assert body["numerator"] == "refund_order_cnt"
    assert body["denominator"] == "order_cnt"
    lineage_ids = [n["metric_id"] for n in body["lineage"]]
    assert "refund_order_cnt" in lineage_ids
    assert "order_cnt" in lineage_ids


def test_metric_detail_not_found(client: TestClient) -> None:
    r = client.get("/api/v1/semantic/metrics/does_not_exist")
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "NOT_FOUND"
