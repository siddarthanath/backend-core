"""FlagRepository — read/write access for feature_flags table."""

# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Standard Library
import uuid
from typing import Optional

# Third Party
from sqlalchemy import select

# Internal
from src.models.flag import FeatureFlag
from src.repositories.base import BaseRepository

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #


class FlagRepository(BaseRepository[FeatureFlag]):
    """Repository for feature flag records."""

    model_class = FeatureFlag

    async def get_by_org(self, org_id: uuid.UUID) -> list[FeatureFlag]:
        """Return all feature flags for an org.

        Args:
            org_id (uuid.UUID): The org's UUID.

        Returns:
            list[FeatureFlag]: All flags for the org.

        """
        stmt = (
            select(FeatureFlag)
            .where(FeatureFlag.org_id == org_id)
            .order_by(FeatureFlag.key)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_org_and_key(
        self, org_id: uuid.UUID, key: str
    ) -> Optional[FeatureFlag]:
        """Return a single flag by org and key.

        Args:
            org_id (uuid.UUID): The org's UUID.
            key (str): The flag key.

        Returns:
            FeatureFlag | None: The flag, or None if not found.

        """
        stmt = (
            select(FeatureFlag)
            .where(FeatureFlag.org_id == org_id)
            .where(FeatureFlag.key == key)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
