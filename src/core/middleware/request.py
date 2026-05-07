"""Request logging middleware — injects request_id into context, logs method/path/status/duration."""

# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Standard Library
import time
import uuid

# Third Party
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# Internal
from src.core.context import set_request_id
from src.utils.logging import setup_logger

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #

logger = setup_logger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Generates a UUID per request, binds it to the async context, and logs completion."""

    async def dispatch(self, request: Request, call_next) -> Response:  # type: ignore[override]
        request_id = str(uuid.uuid4())
        set_request_id(request_id)

        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000

        logger.info(
            "%s %s %s %.1fms rid=%s",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
            request_id,
        )
        response.headers["X-Request-ID"] = request_id
        return response