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
from src.utils.logging import configure_logging, get_logger

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #

log = get_logger(__name__)


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    db_session = DatabaseSession()
    db_session.initialise()
    db_registry.register(db_session, name="default")
    log.info("app.started", name=app_settings.APP_NAME, version=app_settings.APP_VERSION)

    yield

    await db_registry.get("default").close()
    log.info("app.stopped")


def create_app() -> FastAPI:
    """Build and return the configured FastAPI application.

    Returns:
        FastAPI: The assembled application instance.

    """
    configure_logging(debug=app_settings.DEBUG)

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
