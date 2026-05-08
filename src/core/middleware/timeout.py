"""Timeout middleware — cancels requests that exceed the configured timeout."""

# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Standard Library
import asyncio

# Third Party
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

# Internal
from src.configs.settings import app_settings
from src.core.exceptions.envelope import ErrorEnvelope
from src.utils.logging import setup_logger

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #

logger = setup_logger(__name__)


class TimeoutMiddleware(BaseHTTPMiddleware):
    """Cancels any request that takes longer than REQUEST_TIMEOUT_SECONDS.

    Note: asyncio.wait_for covers time-to-first-byte only for streaming responses.
    Non-streaming handlers (the common case) are fully covered.

    """

    async def dispatch(self, request: Request, call_next) -> Response:  # type: ignore[override]
        try:
            return await asyncio.wait_for(
                call_next(request),
                timeout=app_settings.REQUEST_TIMEOUT_SECONDS,
            )
        except asyncio.TimeoutError:
            logger.warning("Request timed out: %s %s", request.method, request.url.path)
            envelope = ErrorEnvelope.from_exception(code="TIMEOUT", message="Request timed out")
            return JSONResponse(status_code=504, content=envelope.model_dump())