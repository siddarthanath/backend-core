"""ErrorEnvelope schema — standard JSON error shape returned by all exception handlers."""

# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Third Party
from pydantic import BaseModel

# Internal
from src.core.context import get_request_id

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #


class ErrorDetail(BaseModel):
    """Inner error object carried by every error response."""

    code: str
    message: str
    detail: str | None
    request_id: str | None


class ErrorEnvelope(BaseModel):
    """Top-level wrapper: { error: { code, message, detail, request_id } }."""

    error: ErrorDetail

    @classmethod
    def from_exception(
        cls,
        code: str,
        message: str,
        detail: str | None = None,
    ) -> "ErrorEnvelope":
        """Build an envelope from exception fields, injecting the current request ID.

        Args:
            code (str): Machine-readable error code (e.g. "AUTH_ERROR").
            message (str): Human-readable summary.
            detail (str | None): Optional extra context.

        Returns:
            ErrorEnvelope: Populated envelope ready for JSON serialisation.

        """
        return cls(
            error=ErrorDetail(
                code=code,
                message=message,
                detail=detail,
                request_id=get_request_id(),
            )
        )