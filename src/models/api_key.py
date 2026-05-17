"""ApiKey model — hashed credentials for programmatic access."""

# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Standard Library
import uuid
from datetime import datetime
from typing import Optional

# Third Party
import sqlalchemy as sa
from sqlmodel import Field, SQLModel

# Internal
from src.models.base import SoftDeleteMixin, TimestampMixin, UUIDMixin

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #


class ApiKey(UUIDMixin, TimestampMixin, SoftDeleteMixin, SQLModel, table=True):
    """API key for programmatic access.

    The raw key is generated once and returned to the user — never stored.
    key_hash (sha256) is used for verification. key_prefix is the first 11
    chars of the raw key ("sk_" + 8 chars) shown in the UI for identification.
    """

    __tablename__ = "api_keys"

    org_id: uuid.UUID = Field(
        foreign_key="organisations.id",
        nullable=False,
        index=True,
    )
    created_by: Optional[uuid.UUID] = Field(
        default=None,
        foreign_key="user_profiles.id",
        nullable=True,
    )
    name: str = Field(nullable=False, max_length=100)
    key_prefix: str = Field(nullable=False, max_length=16)
    key_hash: str = Field(nullable=False, unique=True)
    last_used_at: Optional[datetime] = Field(
        default=None,
        sa_type=sa.DateTime(timezone=True),
    )
    expires_at: Optional[datetime] = Field(
        default=None,
        sa_type=sa.DateTime(timezone=True),
    )
