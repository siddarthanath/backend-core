"""UserRepository — data access for UserProfile records."""

# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Standard Library
import uuid

# Third Party
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

# Internal
from src.models.user import UserProfile
from src.repositories.base import BaseRepository

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #


class UserRepository(BaseRepository[UserProfile]):
    """Repository for UserProfile — all user data access goes through here."""

    model_class = UserProfile

    async def get_by_email(self, email: str) -> UserProfile | None:
        """Fetch a non-deleted user by email address."""
        stmt = (
            select(UserProfile)
            .where(UserProfile.email == email)
            .where(self._not_deleted())
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_stripe_customer_id(self, customer_id: str) -> UserProfile | None:
        """Fetch a user by Stripe customer ID — used during webhook processing."""
        stmt = (
            select(UserProfile)
            .where(UserProfile.stripe_customer_id == customer_id)
            .where(self._not_deleted())
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def upsert_from_supabase(
        self,
        *,
        user_id: uuid.UUID,
        email: str,
        first_name: str | None = None,
        last_name: str | None = None,
    ) -> UserProfile:
        """Return existing profile or create one from Supabase auth data.

        Names are only written on first insert — ON CONFLICT DO NOTHING means any
        user-updated names are never overwritten by JWT metadata on subsequent logins.

        Args:
            user_id (uuid.UUID): Supabase auth UUID (sub claim).
            email (str): Email from the verified JWT.
            first_name (str | None): From JWT user_metadata.full_name split, first login only.
            last_name (str | None): From JWT user_metadata.full_name split, first login only.

        Returns:
            UserProfile: The existing or newly created profile.

        """
        # INSERT ... ON CONFLICT DO NOTHING is atomic — eliminates the race condition where two
        # concurrent first requests for the same user both see no row and both attempt to insert.
        values: dict = {"id": user_id, "email": email}
        if first_name is not None:
            values["first_name"] = first_name
        if last_name is not None:
            values["last_name"] = last_name
        stmt = (
            pg_insert(UserProfile)
            .values(**values)
            .on_conflict_do_nothing(index_elements=["id"])
        )
        await self.session.execute(stmt)
        result = await self.get_by_id(user_id)
        assert result is not None
        return result
