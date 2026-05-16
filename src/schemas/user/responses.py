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
    """Extended profile returned by GET /user/me — includes billing and org context."""

    org_count: int = 0
    # B2C: personal org is auto-created on first login and returned here so the
    # frontend can use it for checkout without a separate /orgs fetch.
    # B2B: remove org_id and let clients call GET /orgs to discover team workspaces.
    org_id: uuid.UUID | None = None
    # plan is intentionally absent — fetch it from GET /billing/{org_id}/subscription.
    # Putting plan here would require a billing lookup on every auth check.
