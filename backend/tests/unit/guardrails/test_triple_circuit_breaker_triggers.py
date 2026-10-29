"""三重熔断：max_steps / max_tokens / max_wall_clock 三个独立限制各自触发。"""
import pytest

from app.guardrails.circuit import (
    CircuitBreakerReason,
    CircuitBreakerTrippedError,
    TripleCircuitBreaker,
)


def test_max_steps_triggers():
    cb = TripleCircuitBreaker(max_steps=3, max_tokens=1000, max_wall_clock_seconds=100)
    cb.step()
    cb.step()
    cb.step()
    with pytest.raises(CircuitBreakerTrippedError) as e:
        cb.step()
    assert e.value.reason == CircuitBreakerReason.MAX_STEPS


def test_max_tokens_triggers():
    cb = TripleCircuitBreaker(max_steps=100, max_tokens=10, max_wall_clock_seconds=100)
    with pytest.raises(CircuitBreakerTrippedError) as e:
        cb.step(tokens=11)
    assert e.value.reason == CircuitBreakerReason.MAX_TOKENS


def test_max_wall_clock_triggers():
    # 注入可控时钟：第一次读 0，之后读 999（超过 max_wall_clock）
    calls = iter([0.0, 999.0])
    cb = TripleCircuitBreaker(
        max_steps=100, max_tokens=1000, max_wall_clock_seconds=10, clock=lambda: next(calls)
    )
    with pytest.raises(CircuitBreakerTrippedError) as e:
        cb.step()
    assert e.value.reason == CircuitBreakerReason.MAX_WALL_CLOCK


def test_limits_are_independent():
    """三个限制独立：步骤超限不影响 token 计数判断。"""
    cb = TripleCircuitBreaker(max_steps=2, max_tokens=5, max_wall_clock_seconds=100)
    cb.step(tokens=3)  # 步骤1，token 3（未超 5）
    assert cb.snapshot()["steps"] == 1 and cb.snapshot()["tokens"] == 3
