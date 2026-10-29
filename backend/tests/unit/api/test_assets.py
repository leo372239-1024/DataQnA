"""资产 API 与权限裁剪契约测试。"""
from __future__ import annotations

from fastapi.testclient import TestClient


def test_list_assets_default_analyst(client: TestClient) -> None:
    r = client.get("/api/v1/assets", headers={"X-Roles": "analyst"})
    assert r.status_code == 200
    ids = [a["id"] for a in r.json()]
    # analyst 角色应能看到全部资产（含需要 analyst 权限的 export_report/file_export）
    assert "export_report" in ids
    assert "sql_query" in ids


def test_assets_scope_filter_by_role(client: TestClient) -> None:
    # viewer 角色：只能看到 permissions 为空的公共资产
    r = client.get("/api/v1/assets", headers={"X-Roles": "viewer"})
    assert r.status_code == 200
    ids = [a["id"] for a in r.json()]
    assert "export_report" not in ids  # 需要 analyst 角色
    assert "file_export" not in ids
    assert "sql_query" in ids  # 公共资产


def test_assets_exclude_deprecated(client: TestClient) -> None:
    r = client.get("/api/v1/assets", headers={"X-Roles": "analyst"})
    assert r.status_code == 200
    assert all(not a["deprecated"] for a in r.json())
