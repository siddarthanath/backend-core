"""BodySizeLimitMiddleware — reject oversized request bodies before they reach handlers."""

# Standard Library
# (none)

# Third-Party Library
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

# Private Library
from src.core.exceptions.envelope import ErrorEnvelope
from src.utils.logging import get_logger

log = get_logger(__name__)

# File uploads bypass this entirely: the frontend requests a pre-signed URL from the backend,
# then uploads directly to Supabase Storage — file bytes never reach FastAPI.
# This limit applies to JSON request bodies only.
_DEFAULT_MAX_BYTES = 1 * 1024 * 1024  # 1 MB


class BodySizeLimitMiddleware(BaseHTTPMiddleware):
    """Return 413 if the Content-Length header exceeds the configured cap.

    Defends against trivial payload DoS attacks (large JSON bodies consuming
    server memory before FastAPI begins parsing). Does not buffer the body.
    Chunked encoding is rejected outright — it carries no Content-Length header
    and would otherwise bypass the size check entirely.

    Deployment note: clients that omit Content-Length entirely bypass this check.
    Set an independent body size limit on your reverse proxy as a first line of
    defence (nginx: `client_max_body_size 1m;`, Railway/Render: platform setting).
    """

    def __init__(self, app: object, max_bytes: int = _DEFAULT_MAX_BYTES) -> None:
        super().__init__(app)  # type: ignore[arg-type]
        self.max_bytes = max_bytes

    async def dispatch(self, request: Request, call_next: object) -> Response:
        if request.headers.get("transfer-encoding", "").lower() == "chunked":
            return JSONResponse(
                status_code=411,
                content=ErrorEnvelope.from_exception(
                    code="LENGTH_REQUIRED",
                    message="Chunked transfer encoding is not supported",
                ).model_dump(),
            )

        content_length = request.headers.get("content-length")
        if content_length is not None:
            try:
                length = int(content_length)
            except ValueError:
                return JSONResponse(
                    status_code=400,
                    content=ErrorEnvelope.from_exception(
                        code="BAD_REQUEST",
                        message="Invalid Content-Length header",
                    ).model_dump(),
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
                    content=ErrorEnvelope.from_exception(
                        code="PAYLOAD_TOO_LARGE",
                        message=f"Request body must not exceed {self.max_bytes // (1024 * 1024)} MB",
                    ).model_dump(),
                )

        return await call_next(request)  # type: ignore[misc]
