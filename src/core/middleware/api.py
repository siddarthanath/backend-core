"""API logging middleware — structured request/response logging for debugging."""

# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Standard Library
import logging

# Third Party
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, StreamingResponse

# Internal
from src.utils.logging import get_logger
from src.utils.middleware import MAX_BODY_LOG_BYTES, _decode_body

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #

log = get_logger(__name__)

SKIP_PATHS = {
    "/",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/health",
    "/healthz",
}
STREAMING_PATHS: set[str] = set()


class APILoggingMiddleware(BaseHTTPMiddleware):
    """Log request/response bodies at DEBUG level with redaction and safe truncation."""

    async def dispatch(self, request: Request, call_next: object) -> Response:
        path = request.url.path
        if path in SKIP_PATHS:
            return await call_next(request)  # type: ignore[misc]

        debug_enabled = log.is_enabled_for(logging.DEBUG)

        if debug_enabled and request.method != "GET" and path not in STREAMING_PATHS:
            try:
                request_body = await request.body()
                if request_body:
                    log.debug("request.body", body=_decode_body(request_body))

                async def receive() -> dict[str, object]:
                    return {"type": "http.request", "body": request_body, "more_body": False}

                request._receive = receive  # type: ignore[method-assign]
            except Exception:
                log.exception("request.body_logging_failed")

        response = await call_next(request)  # type: ignore[misc]

        content_type = response.headers.get("content-type", "")
        is_json = "application/json" in content_type

        if not debug_enabled or not is_json or isinstance(response, StreamingResponse) or path in STREAMING_PATHS:
            return response

        try:
            response_body = b""
            async for chunk in response.body_iterator:
                response_body += chunk

            if response_body:
                # Slice for logging only — always serve the full body
                log.debug(
                    "response.body",
                    body=_decode_body(response_body[:MAX_BODY_LOG_BYTES]),
                    status=response.status_code,
                )

            return Response(
                content=response_body,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=response.media_type,
            )
        except Exception:
            log.exception("response.body_logging_failed")
            return response
