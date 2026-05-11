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
