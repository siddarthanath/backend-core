"""CORS middleware — origins loaded from settings, never hardcoded."""

# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Third Party
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Internal
from src.configs.settings import app_settings

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #


def add_cors(app: FastAPI) -> None:
    """Register CORSMiddleware with origins from AppSettings.

    Args:
        app (FastAPI): The application instance.

    """
    app.add_middleware(
        CORSMiddleware,
        allow_origins=app_settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )