"""FastAPI 应用入口：app factory + lifespan + 中央异常处理。"""
from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.container import get_container
from app.core.errors import DomainError
from app.core.logging import configure_logging, get_logger

logger = get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    configure_logging(settings.debug)
    # 启动预检：加载语义层 + 资产注册表，尽早暴露配置错误
    container = get_container()
    reg = container.registry
    assets = container.assets
    logger.info(
        "app_starting",
        app_name=settings.app_name,
        llm_provider=settings.llm_provider,
        metrics=len(reg.metrics),
        dimensions=len(reg.dimensions),
        assets=len(assets.assets),
        semantic_version=reg.semantic_version,
    )
    yield
    logger.info("app_stopped")


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name, lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(DomainError)
    async def domain_error_handler(request: Request, exc: DomainError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status,
            content={
                "error": {
                    "code": exc.code,
                    "detail": exc.detail,
                    "failure_code": exc.failure_code,
                }
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={"error": {"code": "VALIDATION_ERROR", "detail": str(exc)}},
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.error("unhandled_error", error=str(exc), path=str(request.url.path))
        return JSONResponse(
            status_code=500,
            content={"error": {"code": "INTERNAL", "detail": "internal server error"}},
        )

    app.include_router(api_router)

    @app.get("/health")
    async def health() -> dict[str, Any]:
        return {"status": "ok", "app": settings.app_name}

    @app.get("/api/v1/meta")
    async def meta() -> dict[str, Any]:
        container = get_container()
        reg = container.registry
        return {
            "app": settings.app_name,
            "semantic_version": reg.semantic_version,
            "metric_count": len(reg.metrics),
            "dimension_count": len(reg.dimensions),
            "asset_count": len(container.assets.assets),
            "snapshot_date": settings.snapshot_date,
            "llm_provider": settings.llm_provider,
        }

    return app


app = create_app()
