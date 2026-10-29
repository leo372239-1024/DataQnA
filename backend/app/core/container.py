"""应用容器：懒加载单例（registry / gateway / orchestrator / router / audit / store）。

api 与 evals/workers 共享同一批服务单例，避免重复加载 YAML 真相源。
加载路径相对包根解析，不依赖进程 cwd。
"""
from __future__ import annotations

import threading
from collections.abc import Callable
from pathlib import Path
from typing import Any, TypeVar, cast

from app.agent.orchestrator import Orchestrator
from app.agent.run_store import RunStore
from app.guardrails.audit import AuditLogger
from app.observability.store import TraceStore
from app.query.gateway import QueryGateway
from app.routing.registry import AssetRegistry
from app.routing.router import Router
from app.semantic.registry import MetricRegistry

_PKG_ROOT = Path(__file__).resolve().parent.parent  # backend/app
_METRICS_YAML = _PKG_ROOT / "seed" / "metrics" / "registry.yaml"
_ASSETS_YAML = _PKG_ROOT / "seed" / "assets" / "registry.yaml"

T = TypeVar("T")


class Container:
    """线程安全的懒加载容器。属性首次访问时实例化并缓存。"""

    def __init__(self) -> None:
        # 用可重入锁：orchestrator/router 的 _build 在持锁状态下会嵌套访问
        # self.gateway/self.assets 等其它 property（再次进入 _get）。若用普通 Lock
        # 会因非重入而死锁（评测层直接构造 Orchestrator 未覆盖到该生产路径）。
        self._lock = threading.RLock()
        self._cache: dict[str, Any] = {}

    def _get(self, key: str, factory: Callable[[], T]) -> T:
        with self._lock:
            if key not in self._cache:
                self._cache[key] = factory()
            return cast(T, self._cache[key])

    @property
    def registry(self) -> MetricRegistry:
        def _build() -> MetricRegistry:
            return MetricRegistry.from_yaml(_METRICS_YAML)

        return self._get("registry", _build)

    @property
    def gateway(self) -> QueryGateway:
        return self._get("gateway", QueryGateway)

    @property
    def orchestrator(self) -> Orchestrator:
        def _build() -> Orchestrator:
            return Orchestrator(self.registry, self.gateway)

        return self._get("orchestrator", _build)

    @property
    def assets(self) -> AssetRegistry:
        def _build() -> AssetRegistry:
            return AssetRegistry.from_yaml(_ASSETS_YAML)

        return self._get("assets", _build)

    @property
    def router(self) -> Router:
        def _build() -> Router:
            return Router(self.assets)

        return self._get("router", _build)

    @property
    def audit(self) -> AuditLogger:
        return self._get("audit", AuditLogger)

    @property
    def run_store(self) -> RunStore:
        return self._get("run_store", RunStore)

    @property
    def trace_store(self) -> TraceStore:
        return self._get("trace_store", TraceStore)


_container: Container | None = None


def get_container() -> Container:
    global _container
    if _container is None:
        _container = Container()
    return _container


def metrics_yaml_path() -> Path:
    return _METRICS_YAML


def assets_yaml_path() -> Path:
    return _ASSETS_YAML


__all__ = ["Container", "get_container", "metrics_yaml_path", "assets_yaml_path"]
