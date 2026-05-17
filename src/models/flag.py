"""FeatureFlag model — org-scoped on/off feature toggles."""

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


class FeatureFlag(UUIDMixin, TimestampMixin, SQLModel, table=True):
    """Boolean feature toggle scoped to an org.

    Unique on (org_id, key). A flag absent for an org defaults to disabled
    in the evaluation service — never assume enabled.
    """

    __tablename__ = "feature_flags"
    __table_args__ = (
        sa.UniqueConstraint("org_id", "key", name="uq_feature_flag_org_key"),
    )

    org_id: uuid.UUID = Field(
        foreign_key="organisations.id",
        nullable=False,
        index=True,
    )
    key: str = Field(nullable=False, max_length=100)
    enabled: bool = Field(default=False, nullable=False)
    description: Optional[str] = Field(default=None, max_length=300)
