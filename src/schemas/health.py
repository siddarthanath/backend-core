"""Health schemas — response shapes for the health and readiness endpoints."""

# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Standard Library
from datetime import datetime

# Third Party
from pydantic import BaseModel

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #


class HealthResponse(BaseModel):
    """Response for GET /api/v1/health."""

    status: str
    version: str
    timestamp: datetime


class ReadyResponse(BaseModel):
    """Response for GET /api/v1/ready — includes per-dependency check results."""

    status: str
    checks: dict[str, str]