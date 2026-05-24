"""BodySizeLimitMiddleware — reject oversized request bodies before they reach handlers."""

# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Third-Party Library
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

# Private Library
from src.utils.logging import get_logger

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #

log = get_logger(__name__)

# Checked against Content-Length header only. Chunked transfers without Content-Length are not
# capped here — acceptable for a JSON API where chunked uploads are not expected.
# File uploads bypass this entirely: the frontend requests a pre-signed URL from the backend,
# then uploads directly to Supabase Storage (storage.supabase.co) — file bytes never reach
# FastAPI, so this limit only ever applies to JSON request bodies.
_DEFAULT_MAX_BYTES = 1 * 1024 * 1024  # 1 MB


class BodySizeLimitMiddleware(BaseHTTPMiddleware):
    """Return 413 if the Content-Length header exceeds the configured cap.

    Defends against trivial payload DoS attacks (large JSON bodies consuming
    server memory before FastAPI begins parsing). Does not buffer the body.
    """

    def __init__(self, app: object, max_bytes: int = _DEFAULT_MAX_BYTES) -> None:
        super().__init__(app)  # type: ignore[arg-type]
        self.max_bytes = max_bytes

    async def dispatch(self, request: Request, call_next: object) -> Response:
        content_length = request.headers.get("content-length")
        if content_length is not None:
            try:
                length = int(content_length)
            except ValueError:
                return JSONResponse(
                    status_code=400,
                    content={
                        "error": {
                            "code": "BAD_REQUEST",
                            "message": "Invalid Content-Length header",
                        }
                    },
                )
            if length > self.max_bytes:
                log.warning(
                    "request.body_too_large",
                    bytes=length,
                    limit=self.max_bytes,
                    path=request.url.path,
                )
                return JSONResponse(
                    status_code=413,
                    content={
                        "error": {
                            "code": "PAYLOAD_TOO_LARGE",
                            "message": f"Request body must not exceed {self.max_bytes // (1024 * 1024)} MB",
                        }
                    },
                )
        return await call_next(request)  # type: ignore[misc]
