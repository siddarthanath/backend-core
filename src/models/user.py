"""UserProfile model — one row per Supabase auth user."""

# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Standard Library
import uuid

# Third Party
from sqlmodel import Field, SQLModel

# Internal
from src.models.base import SoftDeleteMixin, TimestampMixin

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #


class UserProfile(TimestampMixin, SoftDeleteMixin, SQLModel, table=True):
    """Application-level user profile mirroring Supabase auth.users.

    The id is the Supabase auth UUID (sub claim) — caller provides it, never auto-generated.
    Supabase owns auth; this table owns application data.

    """

    __tablename__ = "user_profiles"

    id: uuid.UUID = Field(
        primary_key=True,
        description="Supabase auth UUID (sub claim)",
    )
    email: str = Field(
        index=True,
        unique=True,
        max_length=320,
        description="Primary email — kept in sync with Supabase auth.users",
    )
    first_name: str | None = Field(default=None, max_length=100)
    last_name: str | None = Field(default=None, max_length=100)
    stripe_customer_id: str | None = Field(
        default=None,
        unique=True,
        index=True,
        description="Stripe customer ID — set when user initiates first checkout",
    )
