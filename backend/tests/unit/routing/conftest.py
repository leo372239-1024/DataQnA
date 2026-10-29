"""routing 单测共享 fixture。"""
import pytest

from app.routing.registry import AssetRegistry
from app.routing.router import Router


@pytest.fixture
def registry() -> AssetRegistry:
    return AssetRegistry.from_yaml("app/seed/assets/registry.yaml")


@pytest.fixture
def router(registry: AssetRegistry) -> Router:
    return Router(registry)
