"""Billing endpoints — subscription info, Stripe checkout, portal, and webhooks."""

# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Standard Library
import uuid

# Third Party
from fastapi import APIRouter, Header, Request

# Internal
from src.core.dependencies import BillingSvc, CurrentUserID
from src.core.middleware.rate_limit import limiter
from src.schemas.billing.requests import CreateCheckoutRequest, CreatePortalRequest
from src.schemas.billing.responses import CheckoutResponse, PortalResponse, SubscriptionResponse
from src.schemas.common import MessageResponse

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #

router = APIRouter(tags=["Billing"])


@router.get("/orgs/{org_id}/billing", response_model=SubscriptionResponse)
@limiter.limit("60/minute")
async def get_subscription(
    request: Request,
    org_id: uuid.UUID,
    user_id: CurrentUserID,
    service: BillingSvc,
) -> SubscriptionResponse:
    """Return the current subscription state for an org."""
    return await service.get_subscription(org_id, user_id)


@router.post("/orgs/{org_id}/billing/checkout", response_model=CheckoutResponse, status_code=201)
@limiter.limit("10/minute")
async def create_checkout(
    request: Request,
    org_id: uuid.UUID,
    body: CreateCheckoutRequest,
    user_id: CurrentUserID,
    service: BillingSvc,
) -> CheckoutResponse:
    """Initiate a Stripe checkout session to upgrade the org's plan."""
    return await service.create_checkout(
        org_id,
        user_id,
        plan=body.plan,
        period=body.period,
        success_url=str(body.success_url),
        cancel_url=str(body.cancel_url),
    )


@router.post("/orgs/{org_id}/billing/portal", response_model=PortalResponse, status_code=201)
@limiter.limit("10/minute")
async def create_portal(
    request: Request,
    org_id: uuid.UUID,
    body: CreatePortalRequest,
    user_id: CurrentUserID,
    service: BillingSvc,
) -> PortalResponse:
    """Open the Stripe customer portal for billing management."""
    return await service.create_portal(org_id, user_id, return_url=str(body.return_url))


@router.post("/billing/webhook", response_model=MessageResponse)
async def stripe_webhook(
    request: Request,
    service: BillingSvc,
    stripe_signature: str = Header(alias="stripe-signature"),
) -> MessageResponse:
    """Receive and process Stripe webhook events. No auth — verified by signature."""
    payload = await request.body()
    await service.handle_webhook(payload, stripe_signature)
    return MessageResponse(message="ok")
