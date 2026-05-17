"""BillingOrchestrator and StripeBillingService — billing lifecycle coordination."""

# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Standard Library
import uuid
from datetime import datetime, timezone

# Third Party
import anyio.to_thread
import stripe

# Internal
from src.configs.settings import external_settings
from src.constants import BillingPeriod, Plan, Role, SubscriptionStatus
from src.core.exceptions.types import ConflictError, ForbiddenError, NotFoundError
from src.models.billing import Subscription
from src.repositories.billing import SubscriptionRepository
from src.repositories.org import MembershipRepository, OrgRepository
from src.schemas.billing.responses import CheckoutResponse, PortalResponse, SubscriptionResponse
from src.services.billing.interface import BaseBillingService
from src.utils.logging import get_logger

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #

log = get_logger(__name__)


def _build_price_map() -> dict[tuple[Plan, BillingPeriod], str]:
    return {
        (Plan.PRO, BillingPeriod.MONTHLY): external_settings.STRIPE_PRO_MONTHLY_PRICE_ID,
        (Plan.PRO, BillingPeriod.YEARLY): external_settings.STRIPE_PRO_YEARLY_PRICE_ID,
        (Plan.MAX, BillingPeriod.MONTHLY): external_settings.STRIPE_MAX_MONTHLY_PRICE_ID,
        (Plan.MAX, BillingPeriod.YEARLY): external_settings.STRIPE_MAX_YEARLY_PRICE_ID,
    }


class StripeBillingService(BaseBillingService):
    """Stripe implementation of BaseBillingService. All Stripe API calls live here."""

    def __init__(self) -> None:
        stripe.api_key = external_settings.STRIPE_SECRET_KEY
        self._webhook_secret = external_settings.STRIPE_WEBHOOK_SECRET

    async def create_checkout_session(
        self,
        customer_id: str | None,
        price_id: str,
        org_id: str,
        success_url: str,
        cancel_url: str,
    ) -> tuple[str, str]:
        """Create a Stripe checkout session.

        Args:
            customer_id (str | None): Existing Stripe customer ID, or None.
            price_id (str): Stripe price ID for the target plan.
            org_id (str): Org UUID stored in Stripe metadata.
            success_url (str): Redirect URL on successful payment.
            cancel_url (str): Redirect URL on cancelled checkout.

        Returns:
            tuple[str, str]: (checkout_url, stripe_customer_id).

        """
        params: dict = {
            "mode": "subscription",
            "line_items": [{"price": price_id, "quantity": 1}],
            "success_url": success_url,
            "cancel_url": cancel_url,
            "metadata": {"org_id": org_id},
        }
        # ONE-TIME CREDIT TOP-UPS: if the product later supports purchasing usage credits
        # (e.g. extra AI quota), create a separate checkout handler using mode="payment"
        # with customer_creation="always". Do NOT add it here — this method is
        # subscription-only. Stripe auto-creates a customer in subscription mode.
        if customer_id:
            params["customer"] = customer_id

        session = await anyio.to_thread.run_sync(lambda: stripe.checkout.Session.create(**params))
        return session.url, session.customer  # type: ignore[return-value]

    async def create_portal_session(self, customer_id: str, return_url: str) -> str:
        """Create a Stripe customer portal session URL.

        Args:
            customer_id (str): Stripe customer ID for the org.
            return_url (str): Return URL after the portal session.

        Returns:
            str: Stripe portal session URL.

        """
        session = await anyio.to_thread.run_sync(
            lambda: stripe.billing_portal.Session.create(
                customer=customer_id,
                return_url=return_url,
            )
        )
        return session.url  # type: ignore[return-value]

    async def modify_subscription(self, stripe_sub_id: str, price_id: str) -> None:
        """Swap the price on an active subscription (immediate upgrade with proration).

        Args:
            stripe_sub_id (str): Stripe subscription ID to modify.
            price_id (str): New Stripe price ID for the target plan/period.

        """
        raw_sub = await anyio.to_thread.run_sync(lambda: stripe.Subscription.retrieve(stripe_sub_id))
        item_id: str = raw_sub["items"]["data"][0]["id"]
        await anyio.to_thread.run_sync(
            lambda: stripe.Subscription.modify(
                stripe_sub_id,
                items=[{"id": item_id, "price": price_id}],
                # Charge the prorated difference immediately rather than crediting the next invoice
                proration_behavior="always_invoice",
            )
        )

    async def cancel_subscription(self, stripe_sub_id: str) -> None:
        """Mark a subscription to cancel at the end of the current billing period.

        Args:
            stripe_sub_id (str): Stripe subscription ID to cancel.

        """
        await anyio.to_thread.run_sync(
            lambda: stripe.Subscription.modify(stripe_sub_id, cancel_at_period_end=True)
        )

    async def parse_webhook(self, payload: bytes, sig_header: str) -> dict:
        """Verify Stripe signature and return the parsed event dict.

        Args:
            payload (bytes): Raw request body.
            sig_header (str): Stripe-Signature header value.

        Raises:
            ValueError: If the signature is invalid.

        Returns:
            dict: Parsed Stripe event.

        """
        try:
            event = stripe.Webhook.construct_event(payload, sig_header, self._webhook_secret)
        except stripe.SignatureVerificationError as exc:
            raise ValueError("Invalid Stripe webhook signature") from exc
        return event.to_dict()


class BillingOrchestrator:
    """Coordinates billing business logic: DB state + provider calls."""

    def __init__(
        self,
        subscription_repo: SubscriptionRepository,
        org_repo: OrgRepository,
        membership_repo: MembershipRepository,
        billing_svc: BaseBillingService,
    ) -> None:
        self.subscription_repo = subscription_repo
        self.org_repo = org_repo
        self.membership_repo = membership_repo
        self.billing_svc = billing_svc

    async def get_subscription(
        self, org_id: uuid.UUID, user_id: uuid.UUID
    ) -> SubscriptionResponse:
        """Return the current subscription for an org.

        Args:
            org_id (uuid.UUID): The org's UUID.
            user_id (uuid.UUID): The requesting user's UUID (must be a member).

        Raises:
            NotFoundError: If the org does not exist or user is not a member.

        Returns:
            SubscriptionResponse: Current subscription state.

        """
        org = await self.org_repo.get_by_id(org_id)
        if not org:
            raise NotFoundError("Organisation", org_id)
        if not await self.membership_repo.user_has_role(user_id, org_id, Role.MEMBER):
            raise ForbiddenError("You are not a member of this organisation")

        sub = await self.subscription_repo.upsert_free(org_id)
        return SubscriptionResponse.model_validate(sub)

    async def create_checkout(
        self,
        org_id: uuid.UUID,
        user_id: uuid.UUID,
        plan: Plan,
        period: BillingPeriod,
        success_url: str,
        cancel_url: str,
    ) -> CheckoutResponse:
        """Initiate a Stripe checkout session for an org plan upgrade.

        Args:
            org_id (uuid.UUID): The org's UUID.
            user_id (uuid.UUID): The requesting user's UUID (must be admin/owner).
            plan (Plan): The target plan (PRO or ENTERPRISE).
            success_url (str): Redirect URL on successful payment.
            cancel_url (str): Redirect URL on cancelled checkout.

        Raises:
            ForbiddenError: If the user is not an admin or owner.
            ConflictError: If the org is already on the requested plan.
            NotFoundError: If the org does not exist.

        Returns:
            CheckoutResponse: Stripe checkout session URL.

        """
        org = await self.org_repo.get_by_id(org_id)
        if not org:
            raise NotFoundError("Organisation", org_id)
        if not await self.membership_repo.user_has_role(user_id, org_id, Role.ADMIN):
            raise ForbiddenError("Only admins can manage billing")
        if plan in (Plan.FREE, Plan.ENTERPRISE):
            raise ConflictError("Plan", "plan", plan.value)

        sub = await self.subscription_repo.upsert_free(org_id)
        if sub.plan == plan and sub.status == SubscriptionStatus.ACTIVE:
            raise ConflictError("Subscription", "plan", plan.value)

        price_map = _build_price_map()
        price_id = price_map.get((plan, period))
        if not price_id:
            raise ValueError(f"No Stripe price ID configured for plan={plan.value} period={period.value}")

        checkout_url, stripe_customer_id = await self.billing_svc.create_checkout_session(
            customer_id=org.stripe_customer_id,
            price_id=price_id,
            org_id=str(org_id),
            success_url=success_url,
            cancel_url=cancel_url,
        )


        if not org.stripe_customer_id and stripe_customer_id:
            await self.org_repo.update(org, stripe_customer_id=stripe_customer_id)

        log.info("billing.checkout_created", org_id=str(org_id), plan=plan.value)
        return CheckoutResponse(checkout_url=checkout_url)

    async def upgrade_subscription(
        self,
        org_id: uuid.UUID,
        user_id: uuid.UUID,
        plan: Plan,
        period: BillingPeriod,
    ) -> None:
        """Upgrade an active subscription in-place without going through the portal.

        Only valid when the org already has a Stripe subscription. Use create_checkout
        for new subscribers. Downgrades must go through the portal.

        Args:
            org_id (uuid.UUID): The org's UUID.
            user_id (uuid.UUID): The requesting user's UUID (must be admin/owner).
            plan (Plan): Target plan — must be higher than the current plan.
            period (BillingPeriod): Billing period for the new price.

        Raises:
            ForbiddenError: If the user is not an admin, or org has no active subscription.
            NotFoundError: If the org does not exist.
            ConflictError: If the org is already on the target plan, or no price ID configured.

        """
        org = await self.org_repo.get_by_id(org_id)
        if not org:
            raise NotFoundError("Organisation", org_id)
        if not await self.membership_repo.user_has_role(user_id, org_id, Role.ADMIN):
            raise ForbiddenError("Only admins can manage billing")

        sub = await self.subscription_repo.get_by_org(org_id)
        if not sub or not sub.stripe_subscription_id:
            # No active paid sub — caller should use create_checkout instead
            raise ForbiddenError("No active subscription to upgrade — use checkout to start one")

        if sub.plan == plan:
            raise ConflictError("Subscription", "plan", plan.value)

        price_map = _build_price_map()
        price_id = price_map.get((plan, period))
        if not price_id:
            raise ConflictError("Plan", "price_id", f"{plan.value}/{period.value}")

        await self.billing_svc.modify_subscription(sub.stripe_subscription_id, price_id)
        log.info("billing.subscription_upgraded", org_id=str(org_id), plan=plan.value)

    async def cancel_subscription(
        self,
        org_id: uuid.UUID,
        user_id: uuid.UUID,
        reason: str | None,
    ) -> None:
        """Cancel the active subscription at period end and record the reason.

        Args:
            org_id (uuid.UUID): The org's UUID.
            user_id (uuid.UUID): The requesting user's UUID (must be admin/owner).
            reason (str | None): Optional cancellation reason from the in-app modal.

        Raises:
            ForbiddenError: If the user is not an admin, or org has no active subscription.
            NotFoundError: If the org does not exist.

        """
        org = await self.org_repo.get_by_id(org_id)
        if not org:
            raise NotFoundError("Organisation", org_id)
        if not await self.membership_repo.user_has_role(user_id, org_id, Role.ADMIN):
            raise ForbiddenError("Only admins can manage billing")

        sub = await self.subscription_repo.get_by_org(org_id)
        if not sub or not sub.stripe_subscription_id:
            raise ForbiddenError("No active subscription to cancel")

        await self.billing_svc.cancel_subscription(sub.stripe_subscription_id)
        await self.subscription_repo.update(
            sub,
            cancel_at_period_end=True,
            cancellation_reason=reason,
        )
        log.info("billing.subscription_cancelled", org_id=str(org_id), reason=reason)

    async def create_portal(
        self,
        org_id: uuid.UUID,
        user_id: uuid.UUID,
        return_url: str,
    ) -> PortalResponse:
        """Open the Stripe customer portal for an org.

        Args:
            org_id (uuid.UUID): The org's UUID.
            user_id (uuid.UUID): The requesting user's UUID (must be admin/owner).
            return_url (str): Return URL after the portal session.

        Raises:
            ForbiddenError: If the user is not an admin or owner, or org has no Stripe customer.
            NotFoundError: If the org does not exist.

        Returns:
            PortalResponse: Stripe portal session URL.

        """
        org = await self.org_repo.get_by_id(org_id)
        if not org:
            raise NotFoundError("Organisation", org_id)
        if not await self.membership_repo.user_has_role(user_id, org_id, Role.ADMIN):
            raise ForbiddenError("Only admins can manage billing")
        if not org.stripe_customer_id:
            raise ForbiddenError("No billing account found — complete a checkout first")

        portal_url = await self.billing_svc.create_portal_session(
            customer_id=org.stripe_customer_id,
            return_url=return_url,
        )
        return PortalResponse(portal_url=portal_url)

    async def handle_webhook(self, payload: bytes, sig_header: str) -> None:
        """Process a Stripe webhook event and update subscription state.

        Handles: checkout.session.completed, customer.subscription.updated,
        customer.subscription.deleted, invoice.payment_failed.

        Args:
            payload (bytes): Raw Stripe webhook body.
            sig_header (str): Stripe-Signature header value.

        Raises:
            ValueError: If the webhook signature is invalid.

        """
        event = await self.billing_svc.parse_webhook(payload, sig_header)
        event_type: str = event.get("type", "")
        data = event.get("data", {}).get("object", {})

        log.info("billing.webhook_received", event_type=event_type)

        if event_type == "checkout.session.completed":
            await self._on_checkout_completed(data)
        elif event_type == "customer.subscription.updated":
            await self._on_subscription_updated(data)
        elif event_type == "customer.subscription.deleted":
            await self._on_subscription_deleted(data)
        elif event_type == "invoice.payment_failed":
            await self._on_payment_failed(data)

    async def _on_checkout_completed(self, data: dict) -> None:
        org_id_str: str = data.get("metadata", {}).get("org_id", "")
        stripe_sub_id: str = data.get("subscription", "")
        stripe_customer_id: str = data.get("customer", "")
        if not org_id_str or not stripe_sub_id:
            return

        try:
            org_id = uuid.UUID(org_id_str)
        except ValueError:
            log.warning("billing.webhook_invalid_org_id", org_id=org_id_str)
            return

        org = await self.org_repo.get_by_id(org_id)
        if not org:
            return

        # customer is guaranteed populated on checkout.session.completed — write it now
        if not org.stripe_customer_id and stripe_customer_id:
            await self.org_repo.update(org, stripe_customer_id=stripe_customer_id)

        sub = await self.subscription_repo.get_by_org(org_id)
        if not sub:
            return

        raw_sub = await anyio.to_thread.run_sync(lambda: stripe.Subscription.retrieve(stripe_sub_id))
        stripe_sub: dict = raw_sub.to_dict()
        item = stripe_sub["items"]["data"][0]
        price_id: str = item["price"]["id"]
        plan = self._plan_from_price(price_id)
        period_end = datetime.fromtimestamp(
            item["current_period_end"], tz=timezone.utc
        )

        await self.subscription_repo.update(
            sub,
            plan=plan,
            status=SubscriptionStatus.ACTIVE,
            stripe_subscription_id=stripe_sub_id,
            stripe_price_id=price_id,
            current_period_end=period_end,
            cancel_at_period_end=False,
        )
        log.info("billing.subscription_activated", org_id=org_id_str, plan=plan.value)

    async def _on_subscription_updated(self, data: dict) -> None:
        stripe_sub_id: str = data.get("id", "")
        sub = await self.subscription_repo.get_by_stripe_subscription_id(stripe_sub_id)
        if not sub:
            return

        item = data["items"]["data"][0]
        price_id: str = item["price"]["id"]
        plan = self._plan_from_price(price_id)
        status_str: str = data.get("status", "active")
        try:
            status = SubscriptionStatus(status_str)
        except ValueError:
            status = SubscriptionStatus.ACTIVE
        period_end = datetime.fromtimestamp(item["current_period_end"], tz=timezone.utc)

        # cancellation_details.feedback is intentionally not read here — Stripe's built-in
        # cancellation survey is disabled in favour of our own in-app modal, so this field
        # will never be present. The reason is captured by POST /billing/cancel instead.
        await self.subscription_repo.update(
            sub,
            plan=plan,
            status=status,
            stripe_price_id=price_id,
            current_period_end=period_end,
            cancel_at_period_end=bool(data.get("cancel_at_period_end", False)),
        )

    async def _on_subscription_deleted(self, data: dict) -> None:
        stripe_sub_id: str = data.get("id", "")
        sub = await self.subscription_repo.get_by_stripe_subscription_id(stripe_sub_id)
        if not sub:
            return

        await self.subscription_repo.update(
            sub,
            plan=Plan.FREE,
            status=SubscriptionStatus.CANCELED,
            stripe_subscription_id=None,
            stripe_price_id=None,
            current_period_end=None,
            cancel_at_period_end=False,
        )

    async def _on_payment_failed(self, data: dict) -> None:
        stripe_sub_id: str = data.get("subscription", "")
        if not stripe_sub_id:
            return
        sub = await self.subscription_repo.get_by_stripe_subscription_id(stripe_sub_id)
        if not sub:
            return
        await self.subscription_repo.update(sub, status=SubscriptionStatus.PAST_DUE)

    def _plan_from_price(self, price_id: str) -> Plan:
        price_map = _build_price_map()
        for (plan, _), pid in price_map.items():
            if pid == price_id:
                return plan
        raise ValueError(f"Unknown Stripe price ID: {price_id}")
