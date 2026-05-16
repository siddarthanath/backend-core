"""Subscription model — one row per org, tracks billing plan and Stripe state."""

# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Standard Library
import uuid
from datetime import datetime
from typing import Optional

# Third Party
import sqlalchemy as sa
from sqlmodel import Field, SQLModel

# Internal
from src.constants import Plan, SubscriptionStatus
from src.models.base import TimestampMixin, UUIDMixin

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #


class Subscription(UUIDMixin, TimestampMixin, SQLModel, table=True):
    """Billing subscription for an org. One row per org, upserted on plan changes.

    Free-tier orgs have a row here too (plan=FREE, no Stripe IDs) so that
    billing status can always be queried without null-checking the org itself.

    """

    __tablename__ = "subscriptions"

    org_id: uuid.UUID = Field(
        foreign_key="organisations.id",
        unique=True,
        index=True,
        nullable=False,
    )
    plan: Plan = Field(default=Plan.FREE, nullable=False, sa_type=sa.Enum(Plan, name="plan", create_type=True))
    status: SubscriptionStatus = Field(default=SubscriptionStatus.ACTIVE, nullable=False, sa_type=sa.Enum(SubscriptionStatus, name="subscriptionstatus", create_type=True))
    stripe_subscription_id: Optional[str] = Field(
        default=None,
        unique=True,
        index=True,
        description="Stripe subscription ID — null for FREE plan",
    )
    stripe_price_id: Optional[str] = Field(
        default=None,
        description="Stripe price ID in use — null for FREE plan",
    )
    current_period_end: Optional[datetime] = Field(
        default=None,
        sa_type=sa.DateTime(timezone=True),
        description="UTC timestamp of the current billing period end",
    )
    cancel_at_period_end: bool = Field(
        default=False,
        description="True when the user has requested cancellation at period end",
    )
