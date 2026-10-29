"""三重熔断器：max_steps / max_tokens / max_wall_clock 三个独立限制，各自独立触发。"""
from __future__ import annotations

import time
from collections.abc import Callable
from enum import StrEnum

from app.core.errors import DomainError


class CircuitBreakerReason(StrEnum):
    MAX_STEPS = "MAX_STEPS"
    MAX_TOKENS = "MAX_TOKENS"
    MAX_WALL_CLOCK = "MAX_WALL_CLOCK"


class CircuitBreakerTrippedError(DomainError):
    code = "CIRCUIT_BREAKER_TRIPPED"
    status = 429
    failure_code = "COST_OVERFLOW"

    def __init__(self, reason: CircuitBreakerReason, detail: str) -> None:
        self.reason = reason
        super().__init__(detail, failure_code="COST_OVERFLOW")


class TripleCircuitBreaker:
    """三个独立上限，逐次在 step() 时校验。超限抛 CircuitBreakerTrippedError 并记录计数器。"""

    def __init__(
        self,
        max_steps: int,
        max_tokens: int,
        max_wall_clock_seconds: float,
        *,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.max_steps = max_steps
        self.max_tokens = max_tokens
        self.max_wall_clock = max_wall_clock_seconds
        self._clock = clock
        self.steps = 0
        self.tokens = 0
        self._start = self._clock()

    def step(self, tokens: int = 0) -> None:
        """记录一步（可带 token 消耗）并校验三个上限。"""
        self.steps += 1
        self.tokens += tokens
        if self.steps > self.max_steps:
            raise CircuitBreakerTrippedError(
                CircuitBreakerReason.MAX_STEPS,
                f"步骤数超限：{self.steps} > {self.max_steps}",
            )
        if self.tokens > self.max_tokens:
            raise CircuitBreakerTrippedError(
                CircuitBreakerReason.MAX_TOKENS,
                f"token 消耗超限：{self.tokens} > {self.max_tokens}",
            )
        elapsed = self._clock() - self._start
        if elapsed > self.max_wall_clock:
            raise CircuitBreakerTrippedError(
                CircuitBreakerReason.MAX_WALL_CLOCK,
                f"墙钟时间超限：{elapsed:.1f}s > {self.max_wall_clock}s",
            )

    def snapshot(self) -> dict[str, int | float]:
        return {
            "steps": self.steps,
            "tokens": self.tokens,
            "elapsed_seconds": round(self._clock() - self._start, 3),
        }
