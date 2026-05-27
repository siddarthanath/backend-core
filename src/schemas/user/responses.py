"""User response schemas — output shapes for user endpoints."""

# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Standard Library
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

# Third-Party Library
from pydantic import BaseModel, ConfigDict

# Private Library
if TYPE_CHECKING:
    from src.models.org import Organisation
    from src.models.user import UserProfile

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
    # B2B: remove org_id/org_name and let clients call GET /orgs to discover team workspaces.
    org_id: uuid.UUID | None = None
    org_name: str | None = None
    # plan is intentionally absent — fetch it from GET /billing/{org_id}/subscription.
    # Putting plan here would require a billing lookup on every auth check.


def build_user_me_response(user: "UserProfile", orgs: "list[Organisation]") -> "UserMeResponse":
    personal_org = next((o for o in orgs if o.is_personal), None)
    return UserMeResponse(
        id=user.id,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        created_at=user.created_at,
        org_count=len(orgs),
        org_id=personal_org.id if personal_org else None,
        org_name=personal_org.name if personal_org else None,
    )
