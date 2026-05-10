"""User response schemas — output shapes for user endpoints."""

# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Standard Library
import uuid
from datetime import datetime

# Third Party
from pydantic import BaseModel, ConfigDict

# Internal
from src.constants import Plan

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #


class UserProfileResponse(BaseModel):
    """Public user profile — returned by PATCH /user/me."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    first_name: str | None
    last_name: str | None
    created_at: datetime


class UserMeResponse(UserProfileResponse):
    """Extended profile returned by GET /user/me — includes billing and org context.

    plan and org_count default to FREE/0 until billing (Round 5) and orgs (Round 4) are wired in.

    """

    plan: Plan = Plan.FREE
    org_count: int = 0
