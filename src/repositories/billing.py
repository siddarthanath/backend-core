"""SubscriptionRepository — data access for org subscriptions."""

# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Standard Library
import uuid

# Third Party
from sqlalchemy.exc import IntegrityError
from sqlmodel import select

# Internal
from src.constants import Plan, SubscriptionStatus
from src.models.billing import Subscription
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
            return await self.create(
                Subscription(org_id=org_id, plan=Plan.FREE, status=SubscriptionStatus.ACTIVE)
            )
        except IntegrityError:
            return await self.get_by_org(org_id)  # type: ignore[return-value]
