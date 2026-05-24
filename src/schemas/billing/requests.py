"""Billing request schemas — validated input for billing endpoints."""

# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Standard Library
from urllib.parse import urlparse

# Third-Party Library
from pydantic import BaseModel, Field, HttpUrl, field_validator

# Private Library
from src.configs.settings import app_settings
from src.constants import BillingPeriod, Plan

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #

_ALLOWED_HOST = urlparse(app_settings.FRONTEND_BASE_URL).hostname


def _validate_origin(url: HttpUrl) -> HttpUrl:
    """Reject URLs not on the configured frontend domain (open redirect prevention)."""
    if url.host != _ALLOWED_HOST:
        raise ValueError(f"URL must be on {_ALLOWED_HOST}")
    return url


class CreateCheckoutRequest(BaseModel):
    """Initiate a Stripe checkout session to upgrade the org's plan."""

    plan: Plan
    period: BillingPeriod
    success_url: HttpUrl
    cancel_url: HttpUrl

    @field_validator("success_url", "cancel_url")
    @classmethod
    def _same_origin(cls, v: HttpUrl) -> HttpUrl:
        return _validate_origin(v)


class CreatePortalRequest(BaseModel):
    """Open the Stripe customer portal for the org's billing management."""

    return_url: HttpUrl

    @field_validator("return_url")
    @classmethod
    def _same_origin(cls, v: HttpUrl) -> HttpUrl:
        return _validate_origin(v)


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
    reason: str | None = Field(default=None, max_length=500)
