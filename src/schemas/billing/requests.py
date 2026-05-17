"""Billing request schemas — validated input for billing endpoints."""

# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Third Party
from pydantic import BaseModel, HttpUrl

# Internal
from src.constants import BillingPeriod, Plan

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #


class CreateCheckoutRequest(BaseModel):
    """Initiate a Stripe checkout session to upgrade the org's plan."""

    plan: Plan
    period: BillingPeriod
    success_url: HttpUrl
    cancel_url: HttpUrl


class CreatePortalRequest(BaseModel):
    """Open the Stripe customer portal for the org's billing management."""

    return_url: HttpUrl


class UpgradeSubscriptionRequest(BaseModel):
    """Upgrade an active subscription in-place without going through the portal.

    Only valid when the target plan is higher than the current plan (FREE < PRO < MAX).
    Downgrades must go through the Stripe portal — use POST /billing/portal instead.
    """

    plan: Plan
    period: BillingPeriod


class CancelSubscriptionRequest(BaseModel):
    """Cancel the active subscription at the end of the current billing period."""

    # Optional — stored for retention analysis; never sent to Stripe
    reason: str | None = None
