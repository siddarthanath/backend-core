"""ApiKeyRepository — read/write access for api_keys table."""

# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Standard Library
import uuid
from typing import Optional

# Third Party
from sqlalchemy import select

# Internal
from src.models.api_key import ApiKey
from src.repositories.base import BaseRepository

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #


class ApiKeyRepository(BaseRepository[ApiKey]):
    """Repository for API key records. Soft-deleted keys are excluded from all reads."""

    model_class = ApiKey

    async def get_by_org(self, org_id: uuid.UUID) -> list[ApiKey]:
        """Return all active (non-revoked) API keys for an org.

        Args:
            org_id (uuid.UUID): The org's UUID.

        Returns:
            list[ApiKey]: Active API keys, newest first.

        """
        stmt = (
            select(ApiKey)
            .where(ApiKey.org_id == org_id)
            .where(self._not_deleted())
            .order_by(ApiKey.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_id_and_org(
        self, key_id: uuid.UUID, org_id: uuid.UUID
    ) -> Optional[ApiKey]:
        """Return an active API key by id scoped to an org.

        Args:
            key_id (uuid.UUID): The API key UUID.
            org_id (uuid.UUID): The org's UUID.

        Returns:
            ApiKey | None: The key, or None if not found or revoked.

        """
        stmt = (
            select(ApiKey)
            .where(ApiKey.id == key_id)
            .where(ApiKey.org_id == org_id)
            .where(self._not_deleted())
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_hash(self, key_hash: str) -> Optional[ApiKey]:
        """Return an active API key by its sha256 hash.

        Args:
            key_hash (str): SHA-256 hex digest of the raw key.

        Returns:
            ApiKey | None: The matching key, or None if not found or revoked.

        """
        stmt = (
            select(ApiKey)
            .where(ApiKey.key_hash == key_hash)
            .where(self._not_deleted())
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
