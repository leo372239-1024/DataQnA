"""LLM 网关：provider 选择、结构化输出约束、重试后拒绝、成本计量。

所有 LLM 调用必须经过本模块（禁止在别处实例化 SDK）。
"""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from app.core.config import settings
from app.core.logging import get_logger
from app.llm.base import LLMClient, LLMRequest, LLMResponse
from app.llm.stub import StubClient

logger = get_logger()


class LLMGateway:
    def __init__(self) -> None:
        self._client: LLMClient = self._build_client()

    def _build_client(self) -> LLMClient:
        if settings.llm_provider == "openai_compat":
            from app.llm.openai_compat import OpenAICompatClient

            return OpenAICompatClient(
                model=settings.llm_model,
                api_key=settings.llm_api_key,
                base_url=settings.llm_base_url,
            )
        return StubClient()

    async def complete(self, req: LLMRequest) -> LLMResponse:
        return await self._client.complete(req)

    async def complete_structured(
        self, req: LLMRequest, validator: Callable[[Any], dict[str, Any]], max_retries: int = 2,
    ) -> dict[str, Any]:
        """结构化输出：Schema 校验 + 重试后拒绝。"""
        req.needs_structured = True
        last_error: str | None = None
        for _attempt in range(max_retries + 1):
            resp = await self._client.complete(req)
            try:
                import json

                parsed = json.loads(resp.text) if isinstance(resp.text, str) else resp.text
                validated = validator(parsed)
                return validated
            except Exception as e:  # noqa: BLE001
                last_error = str(e)
                req.messages.append({"role": "assistant", "content": resp.text})
                req.messages.append(
                    {"role": "user", "content": f"上一步输出不合规：{last_error}，请重试"}
                )
        raise ValueError(f"结构化输出连续 {max_retries + 1} 次校验失败：{last_error}")


_gateway: LLMGateway | None = None


def get_gateway() -> LLMGateway:
    global _gateway
    if _gateway is None:
        _gateway = LLMGateway()
    return _gateway
