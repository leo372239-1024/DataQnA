"""API 层单元测试公共夹具。"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture()
def client() -> TestClient:
    # 非 DB 端点懒加载容器，无需 lifespan；不进入 with 块避免启动预检
    return TestClient(app)
