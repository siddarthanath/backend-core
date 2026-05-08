"""Request-scoped context variables — safe for async, set in middleware, read anywhere."""

# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Standard Library
from contextvars import ContextVar

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #

_request_id: ContextVar[str | None] = ContextVar("request_id", default=None)
_user_id: ContextVar[str | None] = ContextVar("user_id", default=None)


def set_request_id(value: str) -> None:
    """Bind the current request ID to this async context.

    Args:
        value (str): UUID string for the request.

    """
    _request_id.set(value)


def get_request_id() -> str | None:
    """Return the current request ID, or None if not set.

    Returns:
        str | None: The request ID string.

    """
    return _request_id.get()


def set_request_user_id(value: str) -> None:
    """Bind the authenticated user ID to this async context.

    Args:
        value (str): UUID string for the user.

    """
    _user_id.set(value)


def get_request_user_id() -> str | None:
    """Return the current user ID, or None if unauthenticated.

    Returns:
        str | None: The user ID string.

    """
    return _user_id.get()