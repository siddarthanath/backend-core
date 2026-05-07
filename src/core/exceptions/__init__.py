"""Exceptions package — typed exceptions, error envelope, and handler registration."""

# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Internal
from src.core.exceptions.base import CoreException
from src.core.exceptions.envelope import ErrorEnvelope
from src.core.exceptions.handlers import add_exception_handlers
from src.core.exceptions.types import AuthException, NotFoundError, RateLimitError, ValidationError

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #

__all__ = [
    "CoreException",
    "ErrorEnvelope",
    "add_exception_handlers",
    "AuthException",
    "NotFoundError",
    "RateLimitError",
    "ValidationError",
]