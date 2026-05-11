"""Unit tests for BillingOrchestrator — no database, all repositories mocked."""

# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Standard Library
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

# Third Party
import pytest

# Internal
from src.constants import Plan, Role, SubscriptionStatus
from src.core.exceptions.types import ConflictError, ForbiddenError, NotFoundError
from src.repositories.billing import SubscriptionRepository
from src.repositories.org import MembershipRepository, OrgRepository
from src.services.billing.interface import BaseBillingService
from src.services.billing.service import BillingOrchestrator

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #


def make_orchestrator(
    *,
    subscription_repo=None,
    org_repo=None,
    membership_repo=None,
    billing_svc=None,
):
    """Return a BillingOrchestrator wired to mocked dependencies."""
    subscription_repo = subscription_repo or AsyncMock(spec=SubscriptionRepository)
    org_repo = org_repo or AsyncMock(spec=OrgRepository)
    membership_repo = membership_repo or AsyncMock(spec=MembershipRepository)
    billing_svc = billing_svc or AsyncMock(spec=BaseBillingService)
    orchestrator = BillingOrchestrator(
        subscription_repo=subscription_repo,
        org_repo=org_repo,
        membership_repo=membership_repo,
        billing_svc=billing_svc,
    )
    return orchestrator, subscription_repo, org_repo, membership_repo, billing_svc


def make_org(**kwargs):
    org = MagicMock()
    org.id = kwargs.get("id", uuid.uuid4())
    org.stripe_customer_id = kwargs.get("stripe_customer_id", None)
    return org


def make_subscription(**kwargs):
    sub = MagicMock()
    sub.id = kwargs.get("id", uuid.uuid4())
    sub.org_id = kwargs.get("org_id", uuid.uuid4())
    sub.plan = kwargs.get("plan", Plan.FREE)
    sub.status = kwargs.get("status", SubscriptionStatus.ACTIVE)
    sub.stripe_subscription_id = kwargs.get("stripe_subscription_id", None)
    sub.current_period_end = kwargs.get("current_period_end", None)
    sub.cancel_at_period_end = kwargs.get("cancel_at_period_end", False)
    return sub


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_subscription_raises_not_found_for_unknown_org():
    orchestrator, _, org_repo, _, _ = make_orchestrator()
    org_repo.get_by_id.return_value = None

    with pytest.raises(NotFoundError):
        await orchestrator.get_subscription(uuid.uuid4(), uuid.uuid4())


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_subscription_raises_forbidden_for_non_member():
    orchestrator, _, org_repo, membership_repo, _ = make_orchestrator()
    org_repo.get_by_id.return_value = make_org()
    membership_repo.user_has_role.return_value = False

    with pytest.raises(ForbiddenError):
        await orchestrator.get_subscription(uuid.uuid4(), uuid.uuid4())


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_subscription_returns_upserted_free_sub():
    orchestrator, subscription_repo, org_repo, membership_repo, _ = make_orchestrator()
    org = make_org()
    sub = make_subscription(org_id=org.id)
    org_repo.get_by_id.return_value = org
    membership_repo.user_has_role.return_value = True
    subscription_repo.upsert_free.return_value = sub

    result = await orchestrator.get_subscription(org.id, uuid.uuid4())

    subscription_repo.upsert_free.assert_awaited_once_with(org.id)
    assert result.org_id == sub.org_id


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_checkout_raises_forbidden_for_non_admin():
    orchestrator, _, org_repo, membership_repo, _ = make_orchestrator()
    org_repo.get_by_id.return_value = make_org()
    membership_repo.user_has_role.return_value = False

    with pytest.raises(ForbiddenError):
        await orchestrator.create_checkout(
            uuid.uuid4(), uuid.uuid4(), Plan.PRO, "https://success.example.com", "https://cancel.example.com"
        )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_checkout_raises_conflict_for_free_plan():
    orchestrator, _, org_repo, membership_repo, _ = make_orchestrator()
    org_repo.get_by_id.return_value = make_org()
    membership_repo.user_has_role.return_value = True

    with pytest.raises(ConflictError):
        await orchestrator.create_checkout(
            uuid.uuid4(), uuid.uuid4(), Plan.FREE, "https://success.example.com", "https://cancel.example.com"
        )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_checkout_raises_conflict_when_already_on_plan():
    orchestrator, subscription_repo, org_repo, membership_repo, _ = make_orchestrator()
    org_repo.get_by_id.return_value = make_org()
    membership_repo.user_has_role.return_value = True
    subscription_repo.upsert_free.return_value = make_subscription(
        plan=Plan.PRO, status=SubscriptionStatus.ACTIVE
    )

    with pytest.raises(ConflictError):
        await orchestrator.create_checkout(
            uuid.uuid4(), uuid.uuid4(), Plan.PRO, "https://success.example.com", "https://cancel.example.com"
        )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_checkout_calls_billing_svc_and_returns_url():
    orchestrator, subscription_repo, org_repo, membership_repo, billing_svc = make_orchestrator()
    org = make_org()
    org_repo.get_by_id.return_value = org
    membership_repo.user_has_role.return_value = True
    subscription_repo.upsert_free.return_value = make_subscription(plan=Plan.FREE)
    billing_svc.create_checkout_session.return_value = ("https://checkout.stripe.com/xyz", "cus_123")

    with patch("src.services.billing.service._build_price_map", return_value={Plan.PRO: "price_pro_123"}):
        result = await orchestrator.create_checkout(
            org.id, uuid.uuid4(), Plan.PRO, "https://success.example.com", "https://cancel.example.com"
        )

    billing_svc.create_checkout_session.assert_awaited_once()
    assert result.checkout_url == "https://checkout.stripe.com/xyz"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_portal_raises_forbidden_for_non_admin():
    orchestrator, _, org_repo, membership_repo, _ = make_orchestrator()
    org_repo.get_by_id.return_value = make_org()
    membership_repo.user_has_role.return_value = False

    with pytest.raises(ForbiddenError):
        await orchestrator.create_portal(uuid.uuid4(), uuid.uuid4(), "https://return.example.com")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_portal_raises_forbidden_when_no_stripe_customer():
    orchestrator, _, org_repo, membership_repo, _ = make_orchestrator()
    org_repo.get_by_id.return_value = make_org(stripe_customer_id=None)
    membership_repo.user_has_role.return_value = True

    with pytest.raises(ForbiddenError, match="No billing account"):
        await orchestrator.create_portal(uuid.uuid4(), uuid.uuid4(), "https://return.example.com")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_handle_webhook_raises_on_invalid_signature():
    orchestrator, _, _, _, billing_svc = make_orchestrator()
    billing_svc.parse_webhook.side_effect = ValueError("Invalid Stripe webhook signature")

    with pytest.raises(ValueError, match="Invalid Stripe webhook signature"):
        await orchestrator.handle_webhook(b"payload", "bad-sig")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_handle_webhook_ignores_unknown_event_type():
    orchestrator, subscription_repo, _, _, billing_svc = make_orchestrator()
    billing_svc.parse_webhook.return_value = {"type": "unknown.event", "data": {"object": {}}}

    await orchestrator.handle_webhook(b"payload", "sig")

    subscription_repo.update.assert_not_awaited()
