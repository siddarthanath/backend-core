"""Application factory — assembles FastAPI, registers middleware, exceptions, and routers."""

# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Standard Library
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

# Third Party
from fastapi import FastAPI

# Internal
from src.api.router import router
from src.configs.settings import app_settings
from src.core.exceptions import add_exception_handlers
from src.core.middleware import add_middleware
from src.core.registry import db_registry
from src.services.sessions.database import DatabaseSession
from src.utils.logging import setup_logger

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #

logger = setup_logger(__name__)


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Startup: initialise DB, register in registry
    db_session = DatabaseSession()
    db_session.initialise()
    db_registry.register(db_session, name="default")
    logger.info("Application started — %s %s", app_settings.APP_NAME, app_settings.APP_VERSION)

    yield

    # Shutdown: dispose engine, release pool connections
    await db_registry.get("default").close()
    logger.info("Application stopped")


def create_app() -> FastAPI:
    """Build and return the configured FastAPI application.

    Returns:
        FastAPI: The assembled application instance.

    """
    app = FastAPI(
        title=app_settings.APP_NAME,
        version=app_settings.APP_VERSION,
        description="A minimal unified Python interface for backend SaaS products.",
        lifespan=_lifespan,
    )

    add_middleware(app)
    add_exception_handlers(app)
    app.include_router(router)

    return app