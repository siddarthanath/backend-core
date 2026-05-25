"""Billing models — Subscription and StripeWebhookEvent."""

# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Standard Library
import uuid
from datetime import datetime
from typing import Optional

# Third-Party Library
import sqlalchemy as sa
from sqlmodel import Field, SQLModel

# Private Library
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
    plan: Plan = Field(
        default=Plan.FREE,
        nullable=False,
        sa_type=sa.Enum(Plan, name="plan", create_type=True),
    )
    status: SubscriptionStatus = Field(
        default=SubscriptionStatus.ACTIVE,
        nullable=False,
        sa_type=sa.Enum(
            SubscriptionStatus, name="subscriptionstatus", create_type=True
        ),
    )
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
    cancellation_reason: Optional[str] = Field(
        default=None,
        description="Reason captured from the in-app cancellation modal; NULL for portal cancellations",
    )


class StripeWebhookEvent(SQLModel, table=True):
    """Processed Stripe webhook events — used to deduplicate retries.

    Stripe retries webhooks for 72 hours on any non-200 response. Before processing
    any event, check if event_id already exists here. If yes, return 200 immediately.
    If no, process and insert in the same transaction.

    Add new event handlers here — never use a column on `subscriptions` for this;
    a column only remembers the last event ID so delayed retries of older events
    would be reprocessed.

    """

    __tablename__ = "stripe_webhook_events"

    # Stripe event IDs are globally unique strings (evt_xxxxx) — use as PK directly.
    event_id: str = Field(primary_key=True)
    event_type: str = Field(nullable=False)
    processed_at: datetime = Field(
        nullable=False,
        sa_type=sa.DateTime(timezone=True),
    )
