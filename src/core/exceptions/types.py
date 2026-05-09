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
    """Raised when a requested resource does not exist (404).

    Usage: raise NotFoundError("User", user_id)

    """

    def __init__(self, resource: str, id: object) -> None:
        super().__init__(
            code="NOT_FOUND",
            message=f"{resource} not found",
            detail=str(id),
            status_code=404,
        )


class ConflictError(CoreException):
    """Raised when a resource with a unique field already exists (409).

    Usage: raise ConflictError("Organisation", "slug", "my-org")

    """

    def __init__(self, resource: str, field: str, value: object) -> None:
        super().__init__(
            code="CONFLICT",
            message=f"{resource} with {field} '{value}' already exists",
            detail=None,
            status_code=409,
        )


class ForbiddenError(CoreException):
    """Raised when the caller lacks permission to perform an action (403)."""

    def __init__(self, message: str = "Forbidden") -> None:
        super().__init__(code="FORBIDDEN", message=message, detail=None, status_code=403)


class ValidationError(CoreException):
    """Raised when business-level validation fails (422)."""

    def __init__(self, message: str = "Validation error", detail: str | None = None) -> None:
        super().__init__(code="VALIDATION_ERROR", message=message, detail=detail, status_code=422)


class RateLimitError(CoreException):
    """Raised when a client exceeds the request rate limit (429)."""

    def __init__(self, message: str = "Rate limit exceeded", detail: str | None = None) -> None:
        super().__init__(code="RATE_LIMIT_ERROR", message=message, detail=detail, status_code=429)


class ExternalServiceError(CoreException):
    """Raised when a call to an external service (Supabase, Stripe, etc.) fails (502)."""

    def __init__(self, service: str, detail: str | None = None) -> None:
        super().__init__(
            code="EXTERNAL_SERVICE_ERROR",
            message=f"{service} returned an unexpected error",
            detail=detail,
            status_code=502,
        )
