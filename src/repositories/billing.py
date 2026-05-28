"""SubscriptionRepository and StripeWebhookEventRepository — billing data access."""

# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Standard Library
import uuid
from datetime import datetime, timezone

# Third-Party Library
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from sqlmodel import select

# Private Library
from src.constants import Plan, SubscriptionStatus
from src.models.billing import Subscription, StripeWebhookEvent
from src.repositories.base import BaseRepository

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #


class SubscriptionRepository(BaseRepository[Subscription]):
    """Repository for Subscription records."""

    model_class = Subscription

    async def get_by_org(self, org_id: uuid.UUID) -> Subscription | None:
        """Fetch the subscription for an org.

        Args:
            org_id (uuid.UUID): The org's UUID.

        Returns:
            Subscription | None: The subscription, or None if the org has never had one.

        """
        stmt = select(Subscription).where(Subscription.org_id == org_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_stripe_subscription_id(
        self, stripe_subscription_id: str
    ) -> Subscription | None:
        """Fetch a subscription by its Stripe subscription ID (used in webhook handlers).

        Args:
            stripe_subscription_id (str): The Stripe subscription ID.

        Returns:
            Subscription | None: The matching subscription, or None.

        """
        stmt = select(Subscription).where(
            Subscription.stripe_subscription_id == stripe_subscription_id
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def hard_delete_by_org(self, org_id: uuid.UUID) -> None:
        """Hard-delete the subscription for an org — used during account/org deletion.

        Args:
            org_id (uuid.UUID): The org's UUID.

        """
        sub = await self.get_by_org(org_id)
        if sub:
            await self.hard_delete(sub)

    async def upsert_free(self, org_id: uuid.UUID) -> Subscription:
        """Ensure a FREE subscription row exists for an org. Creates it if missing.

        Called when an org is created, so billing status is always queryable.

        Args:
            org_id (uuid.UUID): The org's UUID.

        Returns:
            Subscription: The existing or newly created FREE subscription.

        """
        existing = await self.get_by_org(org_id)
        if existing:
            return existing
        try:
            # Savepoint isolates the insert — IntegrityError rolls back only to here,
            # leaving the outer transaction alive for the fallback get_by_org.
            async with self.session.begin_nested():
                return await self.create(
                    Subscription(
                        org_id=org_id, plan=Plan.FREE, status=SubscriptionStatus.ACTIVE
                    )
                )
        except IntegrityError:
            return await self.get_by_org(org_id)  # type: ignore[return-value]


class StripeWebhookEventRepository:
    """Repository for StripeWebhookEvent — idempotency deduplication for Stripe webhooks."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def exists(self, event_id: str) -> bool:
        """Return True if this Stripe event has already been processed.

        Args:
            event_id (str): Stripe event ID (e.g. evt_xxxxx).

        Returns:
            bool: Whether the event is already recorded.

        """
        stmt = select(StripeWebhookEvent).where(StripeWebhookEvent.event_id == event_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def record(self, event_id: str, event_type: str) -> None:
        """Insert a processed event record.

        Args:
            event_id (str): Stripe event ID.
            event_type (str): Stripe event type (e.g. checkout.session.completed).

        """
        self.session.add(
            StripeWebhookEvent(
                event_id=event_id,
                event_type=event_type,
                processed_at=datetime.now(timezone.utc),
            )
        )
        await self.session.flush()
