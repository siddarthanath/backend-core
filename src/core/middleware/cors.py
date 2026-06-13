"""CORS middleware — origins loaded from settings, never hardcoded."""

# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Third-Party Library
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Private Library
from src.configs.settings import app_settings

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #


def add_cors(app: FastAPI) -> None:
    """Register CORSMiddleware with origins from AppSettings.

    Args:
        app (FastAPI): The application instance.

    """
    # Origin is the real CORS security boundary and stays explicit (CORS_ORIGINS).
    # Methods are listed explicitly too — cheap, and add a verb here if you need one.
    # Headers stay "*" on purpose: restricting them has ~no security value (origin is
    # the gate) but breaks tracing/APM tools that inject custom headers (sentry-trace,
    # baggage, traceparent). Starlette echoes the requested headers, so "*" remains
    # compatible with allow_credentials=True.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=app_settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )
