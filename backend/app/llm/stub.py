"""确定性 stub provider：离线可跑、可复现，用于无密钥运行与评测。

对结构化输出任务返回确定性结果；对自然语言任务返回占位文本。
"""
from __future__ import annotations

import hashlib
import time

from app.llm.base import LLMRequest, LLMResponse


class StubClient:
    """离线确定性 LLM 客户端。"""

    name = "local-stub"

    async def complete(self, req: LLMRequest) -> LLMResponse:
        start = time.monotonic()
        text = self._generate(req)
        token_in = len(req.system) // 4 + sum(len(m.get("content", "")) // 4 for m in req.messages)
        token_out = len(text) // 4
        return LLMResponse(
            text=text, model=self.name, token_in=token_in, token_out=token_out,
            latency_ms=(time.monotonic() - start) * 1000,
        )

    def _generate(self, req: LLMRequest) -> str:
        # 若请求了结构化输出，返回一个合法的 JSON 占位（由调用方 schema 校验兜底）
        if req.needs_structured or req.response_model:
            return '{"result": "stub"}'
        # 确定性摘要
        digest = hashlib.md5(req.system.encode()).hexdigest()[:8]
        return f"[stub:{digest}] 基于确定性规则的本地响应。"
