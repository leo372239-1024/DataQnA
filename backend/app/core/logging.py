"""structlog 结构化日志配置。"""
from __future__ import annotations

import logging
import sys
from typing import Any

import structlog

# 敏感字段白名单：命中即脱敏
_SENSITIVE_KEYS = {"token", "api_key", "authorization", "password", "secret", "cookie"}


def _redact(_logger: Any, _method: str, event_dict: dict[str, Any]) -> dict[str, Any]:
    for key in list(event_dict.keys()):
        if key.lower() in _SENSITIVE_KEYS:
            event_dict[key] = "[REDACTED]"
    return event_dict


def configure_logging(debug: bool = False) -> None:
    level = logging.DEBUG if debug else logging.INFO
    processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        _redact,
    ]
    if debug:
        processors.append(structlog.dev.ConsoleRenderer())
    else:
        processors.append(structlog.processors.JSONRenderer())

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(level),
        cache_logger_on_first_use=True,
    )
    logging.basicConfig(stream=sys.stdout, level=level, format="%(message)s")


def get_logger(name: str = "dataqna") -> Any:
    return structlog.get_logger(name)
