"""Middleware package — exports add_middleware() for factory registration."""

# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Third Party
from fastapi import FastAPI
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

# Internal
from src.core.middleware.cors import add_cors
from src.core.middleware.rate_limit import limiter
from src.core.middleware.request import RequestLoggingMiddleware
from src.core.middleware.timeout import TimeoutMiddleware
from src.core.middleware.api import APILoggingMiddleware

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #


def add_middleware(app: FastAPI) -> None:
    """Register all middleware on the FastAPI app.

    Middleware is applied in reverse registration order (last added = outermost).

    Effective request order:

    CORS
    → SlowAPI
    → RequestLogging
    → APILogging
    → Timeout
    → route handler

    Response flow occurs in reverse order.

    Args:
        app (FastAPI): The application instance.
    """
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    app.add_middleware(TimeoutMiddleware)
    app.add_middleware(APILoggingMiddleware)
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(SlowAPIMiddleware)
    
    add_cors(app)