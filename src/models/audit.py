"""AuditLog model — immutable record of org-level actions."""

# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Standard Library
import uuid
from typing import Optional

# Third Party
import sqlalchemy as sa
from sqlmodel import Field, SQLModel

# Internal
from src.models.base import TimestampMixin, UUIDMixin

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #


class AuditLog(UUIDMixin, TimestampMixin, SQLModel, table=True):
    """Immutable audit event — never updated or soft-deleted.

    Actions use dot-notation: resource.verb (e.g. "api_key.created", "member.invited").
    """

    __tablename__ = "audit_logs"

    org_id: uuid.UUID = Field(
        foreign_key="organisations.id",
        nullable=False,
        index=True,
    )
    actor_id: Optional[uuid.UUID] = Field(
        default=None,
        foreign_key="user_profiles.id",
        nullable=True,
    )
    action: str = Field(nullable=False, max_length=100)
    resource_type: str = Field(nullable=False, max_length=100)
    resource_id: Optional[str] = Field(default=None, max_length=200)
    event_metadata: Optional[dict[str, object]] = Field(
        default=None,
        sa_type=sa.JSON,
    )
