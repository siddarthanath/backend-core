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
    # Methods/headers are listed explicitly rather than "*" — with credentialed
    # requests there's no reason to advertise more than the API actually uses.
    # Add to these lists if you introduce new verbs or custom request headers.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=app_settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "stripe-signature"],
    )
