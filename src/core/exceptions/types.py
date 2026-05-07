"""Typed exceptions — domain-specific exceptions that extend CoreException."""

# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Internal
from src.core.exceptions.base import CoreException

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #


class AuthException(CoreException):
    """Raised when authentication or authorisation fails (401)."""

    def __init__(self, message: str = "Unauthorized", detail: str | None = None) -> None:
        super().__init__(code="AUTH_ERROR", message=message, detail=detail, status_code=401)


class NotFoundError(CoreException):
    """Raised when a requested resource does not exist (404)."""

    def __init__(self, message: str = "Not found", detail: str | None = None) -> None:
        super().__init__(code="NOT_FOUND", message=message, detail=detail, status_code=404)


class ValidationError(CoreException):
    """Raised when business-level validation fails (422)."""

    def __init__(self, message: str = "Validation error", detail: str | None = None) -> None:
        super().__init__(code="VALIDATION_ERROR", message=message, detail=detail, status_code=422)


class RateLimitError(CoreException):
    """Raised when a client exceeds the request rate limit (429)."""

    def __init__(self, message: str = "Rate limit exceeded", detail: str | None = None) -> None:
        super().__init__(code="RATE_LIMIT_ERROR", message=message, detail=detail, status_code=429)