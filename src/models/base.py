"""Base SQLModel mixins shared by all database table models."""

# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Standard Library
import uuid
from datetime import datetime, timezone
from typing import Optional

# Third Party
from sqlmodel import Field, SQLModel

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #


class UUIDMixin(SQLModel):
    """Adds a UUID primary key to a table model."""

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)


class TimestampMixin(SQLModel):
    """Adds created_at and updated_at timestamps to a table model."""

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class SoftDeleteMixin(SQLModel):
    """Adds soft-delete support via a nullable deleted_at timestamp."""

    deleted_at: Optional[datetime] = Field(default=None)

    @property
    def is_deleted(self) -> bool:
        """Return True if this record has been soft-deleted."""
        return self.deleted_at is not None