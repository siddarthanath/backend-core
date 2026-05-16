"""Organisation and Membership models — core multi-tenancy primitives."""

# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Standard Library
import uuid
from typing import Optional

# Third Party
import sqlalchemy as sa
from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel

# Internal
from src.constants import MembershipStatus, Role
from src.models.base import SoftDeleteMixin, TimestampMixin, UUIDMixin

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #


class Organisation(UUIDMixin, TimestampMixin, SoftDeleteMixin, SQLModel, table=True):
    """Top-level tenant. Every multi-tenant resource carries an org_id FK.

    Personal workspaces are also Organisations (is_personal=True) — simplifies
    permission logic: all resource access checks the same membership table.

    """

    __tablename__ = "organisations"

    name: str = Field(nullable=False, max_length=200)
    slug: str = Field(unique=True, index=True, nullable=False, max_length=100)
    is_personal: bool = Field(default=False)
    stripe_customer_id: Optional[str] = Field(
        default=None,
        unique=True,
        index=True,
        description="Set when org initiates first checkout",
    )


class Membership(UUIDMixin, TimestampMixin, SQLModel, table=True):
    """Join table: user ↔ org with role and status.

    A user can belong to many orgs with different roles.
    No soft-delete — memberships are hard-deleted on removal.

    """

    __tablename__ = "memberships"
    __table_args__ = (
        UniqueConstraint("user_id", "org_id", name="uq_membership_user_org"),
    )

    user_id: uuid.UUID = Field(
        foreign_key="user_profiles.id",
        index=True,
        nullable=False,
    )
    org_id: uuid.UUID = Field(
        foreign_key="organisations.id",
        index=True,
        nullable=False,
    )
    role: Role = Field(default=Role.MEMBER, nullable=False, sa_type=sa.Enum(Role, name="role", create_type=True))
    status: MembershipStatus = Field(default=MembershipStatus.INVITED, nullable=False, sa_type=sa.Enum(MembershipStatus, name="membershipstatus", create_type=True))
    invited_by: Optional[uuid.UUID] = Field(
        default=None,
        foreign_key="user_profiles.id",
        description="UUID of the user who sent the invite",
    )
