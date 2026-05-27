"""Org request schemas — validated input for org and membership endpoints."""

# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Standard Library
import re
import uuid

# Third-Party Library
from pydantic import BaseModel, EmailStr, field_validator

# Private Library
from src.constants import Role

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #


class CreateOrgRequest(BaseModel):
    """Create a new organisation."""

    name: str
    slug: str

    @field_validator("slug")
    @classmethod
    def slug_format(cls, v: str) -> str:
        """Enforce lowercase alphanumeric + hyphens only."""
        if not re.fullmatch(r"[a-z0-9-]+", v):
            raise ValueError("slug must be lowercase alphanumeric and hyphens only")
        return v


class UpdateOrgRequest(BaseModel):
    """Update org display name. All fields optional."""

    name: str | None = None


class InviteMemberRequest(BaseModel):
    """Invite an existing user to the org by email."""

    email: EmailStr
    role: Role = Role.MEMBER


class UpdateMemberRoleRequest(BaseModel):
    """Change a member's role. Only owners can perform this."""

    role: Role


class TransferOwnershipRequest(BaseModel):
    """Transfer org ownership to an existing active member."""

    new_owner_id: uuid.UUID
