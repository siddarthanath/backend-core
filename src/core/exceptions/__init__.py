"""Exceptions package — typed exceptions, error envelope, and handler registration."""

# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Private Library
from src.core.exceptions.base import CoreException
from src.core.exceptions.envelope import ErrorEnvelope
from src.core.exceptions.handlers import add_exception_handlers
from src.core.exceptions.types import (
    AccountDeletedError,
    AppValidationError,
    AuthException,
    ConflictError,
    ExternalServiceError,
    ForbiddenError,
    NotFoundError,
    RateLimitError,
)

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #

__all__ = [
    "CoreException",
    "ErrorEnvelope",
    "add_exception_handlers",
    "AccountDeletedError",
    "AppValidationError",
    "AuthException",
    "ConflictError",
    "ExternalServiceError",
    "ForbiddenError",
    "NotFoundError",
    "RateLimitError",
]
