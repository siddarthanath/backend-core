"""UserProfile model — one row per Supabase auth user."""

# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Standard Library
import uuid

# Third-Party Library
from sqlalchemy import Index, text
from sqlmodel import Field, SQLModel

# Private Library
from src.models.base import SoftDeleteMixin, TimestampMixin

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #


class UserProfile(TimestampMixin, SoftDeleteMixin, SQLModel, table=True):
    """Application-level user profile mirroring Supabase auth.users.

    The id is the Supabase auth UUID (sub claim) — caller provides it, never auto-generated.
    Supabase owns auth; this table owns application data.

    """

    __tablename__ = "user_profiles"
    __table_args__ = (
        # Partial unique index — soft-deleted rows excluded so a deleted email can be re-used
        # by a new registrant without hard-deleting historical data.
        Index(
            "ix_user_profiles_email_active",
            "email",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )

    id: uuid.UUID = Field(
        primary_key=True,
        description="Supabase auth UUID (sub claim)",
    )
    email: str = Field(
        max_length=320,
        description="Primary email — kept in sync with Supabase auth.users",
    )
    first_name: str | None = Field(default=None, max_length=100)
    last_name: str | None = Field(default=None, max_length=100)
