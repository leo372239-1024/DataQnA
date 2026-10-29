"""OpenAI 兼容 provider（DeepSeek 等经此接入）。"""
from __future__ import annotations

import time

import httpx

from app.llm.base import LLMRequest, LLMResponse


class OpenAICompatClient:
    name = "openai_compat"

    def __init__(self, model: str, api_key: str, base_url: str) -> None:
        self.model = model
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    async def complete(self, req: LLMRequest) -> LLMResponse:
        start = time.monotonic()
        payload = {
            "model": self.model,
            "messages": [{"role": "system", "content": req.system}, *req.messages],
            "temperature": req.temperature,
            "max_tokens": req.max_tokens,
        }
        headers = {"Authorization": f"Bearer {self.api_key}"}
        async with httpx.AsyncClient(timeout=120) as client:
            r = await client.post(
                f"{self.base_url}/chat/completions", json=payload, headers=headers
            )
            r.raise_for_status()
            data = r.json()
        choice = data["choices"][0]
        msg = choice["message"]
        usage = data.get("usage", {})
        return LLMResponse(
            text=msg.get("content") or "",
            model=data.get("model", self.model),
            token_in=usage.get("prompt_tokens", 0),
            token_out=usage.get("completion_tokens", 0),
            latency_ms=(time.monotonic() - start) * 1000,
        )
