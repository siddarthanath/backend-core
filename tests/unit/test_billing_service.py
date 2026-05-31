"""Unit tests for BillingOrchestrator — no database, all repositories mocked."""

# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Standard Library
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

# Third-Party Library
import pytest
from pydantic import ValidationError

# Private Library
from src.constants import BillingPeriod, Plan, SubscriptionStatus
from src.core.exceptions.types import (
    AppValidationError,
    ConflictError,
    ForbiddenError,
    NotFoundError,
)
from src.repositories.billing import (
    StripeWebhookEventRepository,
    SubscriptionRepository,
)
from src.repositories.org import MembershipRepository, OrgRepository
from src.schemas.billing.requests import (
    CancelSubscriptionRequest,
    CreateCheckoutRequest,
    CreatePortalRequest,
)
from src.services.billing.interface import BaseBillingService
from src.services.billing.service import BillingOrchestrator

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #


def make_orchestrator(
    *,
    subscription_repo=None,
    org_repo=None,
    membership_repo=None,
    billing_svc=None,
    webhook_event_repo=None,
):
    """Return a BillingOrchestrator wired to mocked dependencies."""
    subscription_repo = subscription_repo or AsyncMock(spec=SubscriptionRepository)
    org_repo = org_repo or AsyncMock(spec=OrgRepository)
    membership_repo = membership_repo or AsyncMock(spec=MembershipRepository)
    billing_svc = billing_svc or AsyncMock(spec=BaseBillingService)
    webhook_event_repo = webhook_event_repo or AsyncMock(
        spec=StripeWebhookEventRepository
    )
    webhook_event_repo.exists.return_value = False  # default: new event
    orchestrator = BillingOrchestrator(
        subscription_repo=subscription_repo,
        org_repo=org_repo,
        membership_repo=membership_repo,
        billing_svc=billing_svc,
        webhook_event_repo=webhook_event_repo,
    )
    return (
        orchestrator,
        subscription_repo,
        org_repo,
        membership_repo,
        billing_svc,
        webhook_event_repo,
    )


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
    sub.cancellation_reason = kwargs.get("cancellation_reason", None)
    return sub


def make_stripe_subscription_dict(
    *,
    price_id: str = "price_pro_monthly",
    period_end: int = 9999999999,
    org_id: str = "",
) -> dict:
    """Return a minimal dict shaped like a Stripe Subscription object."""
    return {
        "id": "sub_test123",
        "status": "active",
        "cancel_at_period_end": False,
        "current_period_end": period_end,
        "metadata": {"org_id": org_id} if org_id else {},
        "items": {
            "data": [
                {
                    "price": {"id": price_id},
                }
            ]
        },
    }


class TestBillingRequestSchemas:
    @pytest.mark.unit
    def test_checkout_rejects_external_success_url(self) -> None:
        with pytest.raises(ValidationError, match="URL must be on"):
            CreateCheckoutRequest(
                plan="pro",
                period="monthly",
                success_url="https://evil.com/steal",
                cancel_url="http://localhost:3000/cancel",
            )

    @pytest.mark.unit
    def test_checkout_rejects_external_cancel_url(self) -> None:
        with pytest.raises(ValidationError, match="URL must be on"):
            CreateCheckoutRequest(
                plan="pro",
                period="monthly",
                success_url="http://localhost:3000/success",
                cancel_url="https://evil.com/steal",
            )

    @pytest.mark.unit
    def test_portal_rejects_external_return_url(self) -> None:
        with pytest.raises(ValidationError, match="URL must be on"):
            CreatePortalRequest(return_url="https://evil.com/steal")

    @pytest.mark.unit
    def test_cancel_rejects_reason_over_500_chars(self) -> None:
        with pytest.raises(ValidationError):
            CancelSubscriptionRequest(reason="x" * 501)

    @pytest.mark.unit
    def test_cancel_accepts_reason_at_500_chars(self) -> None:
        req = CancelSubscriptionRequest(reason="x" * 500)
        assert req.reason is not None and len(req.reason) == 500


class TestGetSubscription:
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_raises_not_found_for_unknown_org(self) -> None:
        orchestrator, _, org_repo, _, _, _ = make_orchestrator()
        org_repo.get_by_id.return_value = None

        with pytest.raises(NotFoundError):
            await orchestrator.get_subscription(uuid.uuid4(), uuid.uuid4())

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_raises_forbidden_for_non_member(self) -> None:
        orchestrator, _, org_repo, membership_repo, _, _ = make_orchestrator()
        org_repo.get_by_id.return_value = make_org()
        membership_repo.user_has_role.return_value = False

        with pytest.raises(ForbiddenError):
            await orchestrator.get_subscription(uuid.uuid4(), uuid.uuid4())

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_returns_upserted_free_sub(self) -> None:
        orchestrator, subscription_repo, org_repo, membership_repo, _, _ = (
            make_orchestrator()
        )
        org = make_org()
        sub = make_subscription(org_id=org.id)
        org_repo.get_by_id.return_value = org
        membership_repo.user_has_role.return_value = True
        subscription_repo.upsert_free.return_value = sub

        result = await orchestrator.get_subscription(org.id, uuid.uuid4())

        subscription_repo.upsert_free.assert_awaited_once_with(org.id)
        assert result.org_id == sub.org_id


class TestCreateCheckout:
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_raises_forbidden_for_non_admin(self) -> None:
        orchestrator, _, org_repo, membership_repo, _, _ = make_orchestrator()
        org_repo.get_by_id.return_value = make_org()
        membership_repo.user_has_role.return_value = False

        with pytest.raises(ForbiddenError):
            await orchestrator.create_checkout(
                uuid.uuid4(),
                uuid.uuid4(),
                Plan.PRO,
                BillingPeriod.MONTHLY,
                "https://success.example.com",
                "https://cancel.example.com",
            )

    @pytest.mark.unit
    @pytest.mark.asyncio
    @pytest.mark.parametrize("plan", [Plan.FREE, Plan.ENTERPRISE])
    async def test_raises_conflict_for_non_stripe_plan(self, plan: Plan) -> None:
        orchestrator, _, org_repo, membership_repo, _, _ = make_orchestrator()
        org_repo.get_by_id.return_value = make_org()
        membership_repo.user_has_role.return_value = True

        with pytest.raises(ConflictError):
            await orchestrator.create_checkout(
                uuid.uuid4(),
                uuid.uuid4(),
                plan,
                BillingPeriod.MONTHLY,
                "https://success.example.com",
                "https://cancel.example.com",
            )

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_raises_conflict_when_already_on_plan(self) -> None:
        orchestrator, subscription_repo, org_repo, membership_repo, _, _ = (
            make_orchestrator()
        )
        org_repo.get_by_id.return_value = make_org()
        membership_repo.user_has_role.return_value = True
        subscription_repo.upsert_free.return_value = make_subscription(
            plan=Plan.PRO, status=SubscriptionStatus.ACTIVE
        )

        with pytest.raises(ConflictError):
            await orchestrator.create_checkout(
                uuid.uuid4(),
                uuid.uuid4(),
                Plan.PRO,
                BillingPeriod.MONTHLY,
                "https://success.example.com",
                "https://cancel.example.com",
            )

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_calls_billing_svc_and_returns_url(self) -> None:
        orchestrator, subscription_repo, org_repo, membership_repo, billing_svc, _ = (
            make_orchestrator()
        )
        org = make_org()
        org_repo.get_by_id.return_value = org
        membership_repo.user_has_role.return_value = True
        subscription_repo.upsert_free.return_value = make_subscription(plan=Plan.FREE)
        billing_svc.create_checkout_session.return_value = (
            "https://checkout.stripe.com/xyz",
            "cus_123",
        )

        with patch(
            "src.services.billing.service._build_price_map",
            return_value={(Plan.PRO, BillingPeriod.MONTHLY): "price_pro_monthly_123"},
        ):
            result = await orchestrator.create_checkout(
                org.id,
                uuid.uuid4(),
                Plan.PRO,
                BillingPeriod.MONTHLY,
                "https://success.example.com",
                "https://cancel.example.com",
            )

        billing_svc.create_checkout_session.assert_awaited_once()
        assert result.checkout_url == "https://checkout.stripe.com/xyz"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_raises_when_price_id_not_configured(self) -> None:
        orchestrator, subscription_repo, org_repo, membership_repo, _, _ = (
            make_orchestrator()
        )
        org_repo.get_by_id.return_value = make_org()
        membership_repo.user_has_role.return_value = True
        subscription_repo.upsert_free.return_value = make_subscription(plan=Plan.FREE)

        with patch("src.services.billing.service._build_price_map", return_value={}):
            with pytest.raises(
                AppValidationError, match="No Stripe price ID configured"
            ):
                await orchestrator.create_checkout(
                    uuid.uuid4(),
                    uuid.uuid4(),
                    Plan.PRO,
                    BillingPeriod.MONTHLY,
                    "https://success.example.com",
                    "https://cancel.example.com",
                )

    @pytest.mark.unit
    @pytest.mark.asyncio
    @pytest.mark.parametrize("period", [BillingPeriod.MONTHLY, BillingPeriod.YEARLY])
    async def test_routes_correct_price_id_per_period(
        self, period: BillingPeriod
    ) -> None:
        orchestrator, subscription_repo, org_repo, membership_repo, billing_svc, _ = (
            make_orchestrator()
        )
        org = make_org()
        org_repo.get_by_id.return_value = org
        membership_repo.user_has_role.return_value = True
        subscription_repo.upsert_free.return_value = make_subscription(plan=Plan.FREE)
        billing_svc.create_checkout_session.return_value = (
            "https://checkout.stripe.com/xyz",
            "cus_123",
        )

        price_map = {
            (Plan.PRO, BillingPeriod.MONTHLY): "price_pro_monthly",
            (Plan.PRO, BillingPeriod.YEARLY): "price_pro_yearly",
        }
        with patch(
            "src.services.billing.service._build_price_map", return_value=price_map
        ):
            await orchestrator.create_checkout(
                org.id,
                uuid.uuid4(),
                Plan.PRO,
                period,
                "https://success.example.com",
                "https://cancel.example.com",
            )

        _, call_kwargs = billing_svc.create_checkout_session.call_args
        assert call_kwargs["price_id"] == price_map[(Plan.PRO, period)]


class TestPlanFromPrice:
    @pytest.mark.unit
    def test_raises_on_unknown_price_id(self) -> None:
        _, _, _, _, billing_svc, _ = make_orchestrator()
        orchestrator = BillingOrchestrator(
            subscription_repo=AsyncMock(),
            org_repo=AsyncMock(),
            membership_repo=AsyncMock(),
            billing_svc=billing_svc,
            webhook_event_repo=AsyncMock(spec=StripeWebhookEventRepository),
        )
        with patch(
            "src.services.billing.service._build_price_map",
            return_value={(Plan.PRO, BillingPeriod.MONTHLY): "price_known"},
        ):
            with pytest.raises(ValueError, match="Unknown Stripe price ID"):
                orchestrator._plan_from_price("price_unknown")


class TestCreatePortal:
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_raises_forbidden_for_non_admin(self) -> None:
        orchestrator, _, org_repo, membership_repo, _, _ = make_orchestrator()
        org_repo.get_by_id.return_value = make_org()
        membership_repo.user_has_role.return_value = False

        with pytest.raises(ForbiddenError):
            await orchestrator.create_portal(
                uuid.uuid4(), uuid.uuid4(), "https://return.example.com"
            )

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_raises_forbidden_when_no_stripe_customer(self) -> None:
        orchestrator, _, org_repo, membership_repo, _, _ = make_orchestrator()
        org_repo.get_by_id.return_value = make_org(stripe_customer_id=None)
        membership_repo.user_has_role.return_value = True

        with pytest.raises(ForbiddenError, match="No billing account"):
            await orchestrator.create_portal(
                uuid.uuid4(), uuid.uuid4(), "https://return.example.com"
            )


class TestHandleWebhook:
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_raises_on_invalid_signature(self) -> None:
        orchestrator, _, _, _, billing_svc, _ = make_orchestrator()
        billing_svc.parse_webhook.side_effect = ValueError(
            "Invalid Stripe webhook signature"
        )

        with pytest.raises(AppValidationError, match="Invalid webhook signature"):
            await orchestrator.handle_webhook(b"payload", "bad-sig")

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_skips_duplicate_event(self) -> None:
        orchestrator, subscription_repo, _, _, billing_svc, webhook_event_repo = (
            make_orchestrator()
        )
        webhook_event_repo.exists.return_value = True
        billing_svc.parse_webhook.return_value = {
            "id": "evt_duplicate",
            "type": "checkout.session.completed",
            "data": {"object": {}},
        }

        await orchestrator.handle_webhook(b"payload", "sig")

        subscription_repo.update.assert_not_awaited()
        webhook_event_repo.record.assert_not_awaited()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_records_event_after_processing(self) -> None:
        orchestrator, _, _, _, billing_svc, webhook_event_repo = make_orchestrator()
        billing_svc.parse_webhook.return_value = {
            "id": "evt_new",
            "type": "unknown.event",
            "data": {"object": {}},
        }

        await orchestrator.handle_webhook(b"payload", "sig")

        webhook_event_repo.record.assert_awaited_once_with("evt_new", "unknown.event")

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_ignores_unknown_event_type(self) -> None:
        orchestrator, subscription_repo, _, _, billing_svc, _ = make_orchestrator()
        billing_svc.parse_webhook.return_value = {
            "id": "evt_unknown",
            "type": "unknown.event",
            "data": {"object": {}},
        }

        await orchestrator.handle_webhook(b"payload", "sig")

        subscription_repo.update.assert_not_awaited()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_checkout_completed_does_not_activate_subscription(self) -> None:
        # Subscription activation is handled by customer.subscription.created.
        # checkout.session.completed only maps the stripe_customer_id to the org.
        orchestrator, subscription_repo, org_repo, _, billing_svc, _ = (
            make_orchestrator()
        )
        org_id = uuid.uuid4()
        org = make_org(id=org_id, stripe_customer_id=None)

        billing_svc.parse_webhook.return_value = {
            "id": "evt_checkout",
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "metadata": {"org_id": str(org_id)},
                    "subscription": "sub_test123",
                    "customer": "cus_test123",
                }
            },
        }
        org_repo.get_by_id.return_value = org

        await orchestrator.handle_webhook(b"payload", "sig")

        subscription_repo.update.assert_not_awaited()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_checkout_completed_writes_stripe_customer_id_to_org(self) -> None:
        orchestrator, _, org_repo, _, billing_svc, _ = make_orchestrator()
        org_id = uuid.uuid4()
        org = make_org(id=org_id, stripe_customer_id=None)

        billing_svc.parse_webhook.return_value = {
            "id": "evt_checkout",
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "metadata": {"org_id": str(org_id)},
                    "subscription": "sub_test123",
                    "customer": "cus_new123",
                }
            },
        }
        org_repo.get_by_id.return_value = org

        await orchestrator.handle_webhook(b"payload", "sig")

        org_repo.update.assert_awaited_once_with(org, stripe_customer_id="cus_new123")

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_checkout_completed_skips_customer_update_if_already_set(
        self,
    ) -> None:
        orchestrator, _, org_repo, _, billing_svc, _ = make_orchestrator()
        org_id = uuid.uuid4()
        org = make_org(id=org_id, stripe_customer_id="cus_existing")

        billing_svc.parse_webhook.return_value = {
            "id": "evt_checkout",
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "metadata": {"org_id": str(org_id)},
                    "subscription": "sub_test123",
                    "customer": "cus_existing",
                }
            },
        }
        org_repo.get_by_id.return_value = org

        await orchestrator.handle_webhook(b"payload", "sig")

        org_repo.update.assert_not_awaited()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_checkout_completed_does_nothing_if_org_missing(self) -> None:
        orchestrator, subscription_repo, org_repo, _, billing_svc, _ = (
            make_orchestrator()
        )
        billing_svc.parse_webhook.return_value = {
            "id": "evt_checkout",
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "metadata": {"org_id": str(uuid.uuid4())},
                    "subscription": "sub_test123",
                    "customer": "cus_test123",
                }
            },
        }
        org_repo.get_by_id.return_value = None

        await orchestrator.handle_webhook(b"payload", "sig")

        subscription_repo.update.assert_not_awaited()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_subscription_updated_changes_plan_and_status(self) -> None:
        orchestrator, subscription_repo, _, _, billing_svc, _ = make_orchestrator()
        sub = make_subscription(plan=Plan.FREE)
        subscription_repo.get_by_stripe_subscription_id.return_value = sub

        billing_svc.parse_webhook.return_value = {
            "type": "customer.subscription.updated",
            "data": {
                "object": {
                    "id": "sub_test123",
                    "status": "active",
                    "cancel_at_period_end": True,
                    "current_period_end": 9999999999,
                    "items": {"data": [{"price": {"id": "price_pro_monthly"}}]},
                }
            },
        }

        with patch(
            "src.services.billing.service._build_price_map",
            return_value={(Plan.PRO, BillingPeriod.MONTHLY): "price_pro_monthly"},
        ):
            await orchestrator.handle_webhook(b"payload", "sig")

        _, kwargs = subscription_repo.update.call_args
        assert kwargs["plan"] == Plan.PRO
        assert kwargs["cancel_at_period_end"] is True

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_subscription_deleted_resets_to_free(self) -> None:
        orchestrator, subscription_repo, _, _, billing_svc, _ = make_orchestrator()
        sub = make_subscription(plan=Plan.PRO, stripe_subscription_id="sub_test123")
        subscription_repo.get_by_stripe_subscription_id.return_value = sub

        billing_svc.parse_webhook.return_value = {
            "type": "customer.subscription.deleted",
            "data": {"object": {"id": "sub_test123"}},
        }

        await orchestrator.handle_webhook(b"payload", "sig")

        _, kwargs = subscription_repo.update.call_args
        assert kwargs["plan"] == Plan.FREE
        assert kwargs["status"] == SubscriptionStatus.CANCELED
        assert kwargs["stripe_subscription_id"] is None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_payment_failed_sets_past_due(self) -> None:
        orchestrator, subscription_repo, _, _, billing_svc, _ = make_orchestrator()
        sub = make_subscription(plan=Plan.PRO)
        subscription_repo.get_by_stripe_subscription_id.return_value = sub

        billing_svc.parse_webhook.return_value = {
            "type": "invoice.payment_failed",
            "data": {"object": {"subscription": "sub_test123"}},
        }

        await orchestrator.handle_webhook(b"payload", "sig")

        _, kwargs = subscription_repo.update.call_args
        assert kwargs["status"] == SubscriptionStatus.PAST_DUE

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_payment_failed_does_nothing_if_subscription_not_found(self) -> None:
        orchestrator, subscription_repo, _, _, billing_svc, _ = make_orchestrator()
        subscription_repo.get_by_stripe_subscription_id.return_value = None

        billing_svc.parse_webhook.return_value = {
            "type": "invoice.payment_failed",
            "data": {"object": {"subscription": "sub_missing"}},
        }

        await orchestrator.handle_webhook(b"payload", "sig")

        subscription_repo.update.assert_not_awaited()


class TestSubscriptionCreated:
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_activates_subscription_from_event_data(self) -> None:
        orchestrator, subscription_repo, _, _, billing_svc, _ = make_orchestrator()
        org_id = uuid.uuid4()
        sub = make_subscription(org_id=org_id, plan=Plan.FREE)
        subscription_repo.get_by_org.return_value = sub

        billing_svc.parse_webhook.return_value = {
            "id": "evt_sub_created",
            "type": "customer.subscription.created",
            "data": {
                "object": make_stripe_subscription_dict(
                    price_id="price_pro_monthly",
                    period_end=9999999999,
                    org_id=str(org_id),
                )
            },
        }

        with patch(
            "src.services.billing.service._build_price_map",
            return_value={(Plan.PRO, BillingPeriod.MONTHLY): "price_pro_monthly"},
        ):
            await orchestrator.handle_webhook(b"payload", "sig")

        subscription_repo.update.assert_awaited_once()
        _, kwargs = subscription_repo.update.call_args
        assert kwargs["plan"] == Plan.PRO
        assert kwargs["status"] == SubscriptionStatus.ACTIVE
        assert kwargs["stripe_subscription_id"] == "sub_test123"
        assert kwargs["current_period_end"] is not None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_handles_missing_current_period_end_gracefully(self) -> None:
        orchestrator, subscription_repo, _, _, billing_svc, _ = make_orchestrator()
        org_id = uuid.uuid4()
        sub = make_subscription(org_id=org_id, plan=Plan.FREE)
        subscription_repo.get_by_org.return_value = sub

        sub_data = make_stripe_subscription_dict(
            price_id="price_pro_monthly", org_id=str(org_id)
        )
        del sub_data["current_period_end"]

        billing_svc.parse_webhook.return_value = {
            "id": "evt_sub_created",
            "type": "customer.subscription.created",
            "data": {"object": sub_data},
        }

        with patch(
            "src.services.billing.service._build_price_map",
            return_value={(Plan.PRO, BillingPeriod.MONTHLY): "price_pro_monthly"},
        ):
            await orchestrator.handle_webhook(b"payload", "sig")

        _, kwargs = subscription_repo.update.call_args
        assert kwargs["current_period_end"] is None
        assert kwargs["status"] == SubscriptionStatus.ACTIVE

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_does_nothing_if_no_org_id_in_metadata(self) -> None:
        orchestrator, subscription_repo, _, _, billing_svc, _ = make_orchestrator()

        sub_data = make_stripe_subscription_dict(price_id="price_pro_monthly")
        # no org_id in metadata
        sub_data["metadata"] = {}

        billing_svc.parse_webhook.return_value = {
            "id": "evt_sub_created",
            "type": "customer.subscription.created",
            "data": {"object": sub_data},
        }

        await orchestrator.handle_webhook(b"payload", "sig")

        subscription_repo.update.assert_not_awaited()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_does_nothing_if_subscription_not_found(self) -> None:
        orchestrator, subscription_repo, _, _, billing_svc, _ = make_orchestrator()
        org_id = uuid.uuid4()
        subscription_repo.get_by_org.return_value = None

        billing_svc.parse_webhook.return_value = {
            "id": "evt_sub_created",
            "type": "customer.subscription.created",
            "data": {
                "object": make_stripe_subscription_dict(
                    price_id="price_pro_monthly", org_id=str(org_id)
                )
            },
        }

        with patch(
            "src.services.billing.service._build_price_map",
            return_value={(Plan.PRO, BillingPeriod.MONTHLY): "price_pro_monthly"},
        ):
            await orchestrator.handle_webhook(b"payload", "sig")

        subscription_repo.update.assert_not_awaited()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_unknown_price_id_does_not_raise_or_retry(self) -> None:
        # If _plan_from_price raises ValueError (misconfigured price ID), the webhook
        # must return cleanly — not propagate the error and trigger infinite Stripe retries.
        orchestrator, subscription_repo, _, _, billing_svc, _ = make_orchestrator()
        org_id = uuid.uuid4()
        subscription_repo.get_by_org.return_value = make_subscription(org_id=org_id)

        billing_svc.parse_webhook.return_value = {
            "id": "evt_sub_created",
            "type": "customer.subscription.created",
            "data": {
                "object": make_stripe_subscription_dict(
                    price_id="price_unknown_id", org_id=str(org_id)
                )
            },
        }

        with patch("src.services.billing.service._build_price_map", return_value={}):
            await orchestrator.handle_webhook(b"payload", "sig")

        subscription_repo.update.assert_not_awaited()
