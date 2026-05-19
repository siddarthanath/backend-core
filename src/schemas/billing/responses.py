"""Billing response schemas — output shapes for billing endpoints."""

# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Standard Library
import uuid
from datetime import datetime
from typing import Optional

# Third Party
from pydantic import BaseModel, ConfigDict

# Internal
from src.constants import Plan, SubscriptionStatus

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #


class SubscriptionResponse(BaseModel):
    """Current subscription state for an org."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    org_id: uuid.UUID
    plan: Plan
    status: SubscriptionStatus
    stripe_subscription_id: Optional[str]
    current_period_end: Optional[datetime]
    cancel_at_period_end: bool
    cancellation_reason: Optional[str]
    created_at: datetime


class CheckoutResponse(BaseModel):
    """URL to redirect the user to for Stripe checkout."""

    checkout_url: str


class PortalResponse(BaseModel):
    """URL to redirect the user to for Stripe customer portal."""

    portal_url: str
