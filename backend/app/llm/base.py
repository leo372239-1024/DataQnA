"""LLM 网关基础：协议与请求/响应模型。"""
from __future__ import annotations

from typing import Any, Protocol

from pydantic import BaseModel, Field


class LLMRequest(BaseModel):
    system: str = ""
    messages: list[dict[str, str]] = Field(default_factory=list)
    tools: list[dict[str, Any]] = Field(default_factory=list)
    response_model: str | None = None  # 期望的结构化输出类型标识
    temperature: float = 0.0
    max_tokens: int = 2048
    task: str = "default"  # 路由提示（compliance/structured/summarize/cheap）
    needs_structured: bool = False


class LLMResponse(BaseModel):
    text: str = ""
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    structured: dict[str, Any] | None = None
    model: str = ""
    token_in: int = 0
    token_out: int = 0
    latency_ms: float = 0.0


class LLMClient(Protocol):
    async def complete(self, req: LLMRequest) -> LLMResponse: ...
