"""领域错误类型：业务逻辑抛类型化异常，中央 handler 统一映射 HTTP。"""
from __future__ import annotations


class DomainError(Exception):
    """业务错误的基类。"""

    code: str = "DOMAIN_ERROR"
    status: int = 400
    failure_code: str | None = None  # 9 类 agent 失败分类，agent 相关时必填

    def __init__(self, detail: str, *, failure_code: str | None = None) -> None:
        self.detail = detail
        if failure_code is not None:
            self.failure_code = failure_code
        super().__init__(detail)


class NotFoundError(DomainError):
    code = "NOT_FOUND"
    status = 404


class ValidationError(DomainError):
    code = "VALIDATION_ERROR"
    status = 422


class PermissionDeniedError(DomainError):
    code = "PERMISSION_DENIED"
    status = 403


class AuthenticationError(DomainError):
    code = "AUTHENTICATION_REQUIRED"
    status = 401


class CostLimitExceededError(DomainError):
    code = "COST_LIMIT_EXCEEDED"
    status = 429


class UpstreamError(DomainError):
    code = "UPSTREAM_ERROR"
    status = 502


# ---- Agent 领域专用错误（携带 9 类失败码）----

class NoMatchError(DomainError):
    code = "NO_MATCH"
    failure_code = "NO_MATCH"


class MetricAmbiguityError(DomainError):
    code = "METRIC_AMBIG"
    failure_code = "METRIC_AMBIG"


class RateTrapError(DomainError):
    code = "RATE_TRAP"
    failure_code = "RATE_TRAP"


class CostOverflowError(DomainError):
    code = "COST_OVERFLOW"
    failure_code = "COST_OVERFLOW"
    status = 429


class MissingSecurityContextError(DomainError):
    code = "MISSING_SECURITY_CONTEXT"
    failure_code = "TOOL_MISUSE"
    status = 500
