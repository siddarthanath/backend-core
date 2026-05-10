"""Org response schemas — output shapes for org and membership endpoints."""

# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Standard Library
import uuid
from datetime import datetime
from typing import Optional

# Third Party
from pydantic import BaseModel, ConfigDict

# Internal
from src.constants import MembershipStatus, Role

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #


class OrgResponse(BaseModel):
    """Org summary — returned by create, list, and update endpoints."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    is_personal: bool
    created_at: datetime


class MemberResponse(BaseModel):
    """Membership record — returned by invite, role-change, and member-list endpoints."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    org_id: uuid.UUID
    role: Role
    status: MembershipStatus
    invited_by: Optional[uuid.UUID]
    created_at: datetime
