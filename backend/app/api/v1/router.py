"""v1 路由聚合：挂载全部子路由。"""
from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import answers, assets, evals, questions, semantic, traces

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(questions.router)
api_router.include_router(answers.router)
api_router.include_router(semantic.router)
api_router.include_router(assets.router)
api_router.include_router(traces.router)
api_router.include_router(evals.router)
