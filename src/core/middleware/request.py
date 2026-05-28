"""Request logging middleware — injects request_id into context, logs method/path/status/duration."""

# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Standard Library
import time
import uuid
from collections.abc import Awaitable, Callable

# Third-Party Library
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from structlog.contextvars import bind_contextvars, clear_contextvars

# Private Library
from src.core.context import set_request_id
from src.utils.logging import get_logger

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #

log = get_logger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Generates a UUID per request, binds it to both the async context and structlog
    contextvars, then logs method/path/status/duration on completion."""

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:  # type: ignore[override]
        request_id = str(uuid.uuid4())

        # Clear any context left by a previous request on this worker, then bind fresh values.
        # user_id is added later by the auth dependency once the token is decoded.
        clear_contextvars()
        bind_contextvars(request_id=request_id)

        # Also set the ContextVar so ErrorEnvelope.from_exception() can read it synchronously.
        set_request_id(request_id)

        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:  # Catch-log-reraise: we want the request_id in the exception log before it propagates
            duration_ms = round(
                (time.perf_counter() - start) * 1000,
                1,
            )

            log.exception(
                "request.failed",
                duration_ms=duration_ms,
            )

            raise
        duration_ms = round(
            (time.perf_counter() - start) * 1000,
            1,
        )

        log.info(
            "request.complete",
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            duration_ms=duration_ms,
        )
        response.headers["X-Request-ID"] = request_id
        return response
