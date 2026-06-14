"""Security headers middleware — adds standard hardening headers to every response."""

# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Standard Library
from collections.abc import Awaitable, Callable

# Third-Party Library
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Attach baseline security headers to all responses.

    This API returns only JSON, so the CSP is deliberately strict:
    - default-src 'none': the response references no resources, so nothing should load.
    - nosniff: never let a browser MIME-sniff a JSON body into something executable.
    - DENY framing + no-referrer: this API is never embedded or navigated to directly.

    The strict CSP is skipped for HTML responses so it does not break the built-in
    interactive docs (/docs, /redoc), whose Swagger/ReDoc assets would otherwise be
    blocked. The browser-facing app sets its own (looser) CSP — see next.config.ts.
    """

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:  # type: ignore[override]
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        if "text/html" not in response.headers.get("content-type", ""):
            response.headers["Content-Security-Policy"] = "default-src 'none'"
        return response
