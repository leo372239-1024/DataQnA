"""PII 脱敏：在持久化（审计日志/反思）之前对载荷做脱敏。

必须在「持久化源头」应用，而非渲染时应用，避免遗漏的 UI 路径泄露。
"""
from __future__ import annotations

import re
from typing import Any

_EMAIL_RE = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")
_PHONE_RE = re.compile(r"\b1[3-9]\d{9}\b")
_IDCARD_RE = re.compile(r"\b\d{17}[\dXx]\b")
_BANKCARD_RE = re.compile(r"\b\d{13,19}\b")


def desensitize(payload: Any) -> Any:
    """递归脱敏：字符串替换 PII；dict/list 递归；其他原样返回。"""
    if isinstance(payload, str):
        s = _EMAIL_RE.sub("[EMAIL]", payload)
        s = _IDCARD_RE.sub("[IDCARD]", s)
        s = _PHONE_RE.sub("[PHONE]", s)
        s = _BANKCARD_RE.sub("[BANKCARD]", s)
        return s
    if isinstance(payload, dict):
        return {k: desensitize(v) for k, v in payload.items()}
    if isinstance(payload, (list, tuple)):
        return [desensitize(v) for v in payload]
    return payload
