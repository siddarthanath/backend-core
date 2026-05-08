"""Health endpoints — liveness and readiness checks."""

# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Standard Library
from datetime import datetime, timezone

# Third Party
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

# Internal
from src.configs.settings import app_settings
from src.core.dependencies.database import get_db
from src.schemas.health import HealthResponse, ReadyResponse

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Liveness check - returns 200 if the process is running."""
    return HealthResponse(
        status="ok",
        version=app_settings.APP_VERSION,
        timestamp=datetime.now(timezone.utc),
    )


@router.get("/ready", response_model=ReadyResponse)
async def ready(db: AsyncSession = Depends(get_db)) -> ReadyResponse:
    """Readiness check - verifies the database is reachable.

    Follows the Kubernetes liveness/readiness probe convention: each dependency
    is reported as "ok" or "error" in the checks map, not as an HTTP status code.
    """
    try:
        await db.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception:
        db_status = "error"

    return ReadyResponse(status="ready", checks={"database": db_status})