"""ApiKeyService — create, list, revoke, and verify API keys."""

# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Standard Library
import hashlib
import secrets
import uuid
from datetime import datetime
from typing import Optional

# Internal
from src.constants import Role
from src.core.exceptions.types import ForbiddenError, NotFoundError
from src.models.api_key import ApiKey
from src.repositories.api_key import ApiKeyRepository
from src.repositories.org import MembershipRepository, OrgRepository
from src.schemas.api_key.responses import ApiKeyCreatedResponse, ApiKeyResponse
from src.utils.logging import get_logger

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #

log = get_logger(__name__)

_KEY_PREFIX_LEN = 11  # "sk_" + 8 chars from token


def _generate_key() -> tuple[str, str, str]:
    """Return (raw_key, key_prefix, key_hash).

    raw_key is shown to the user once; key_hash is persisted; key_prefix is
    shown in the UI for identification (never the full key).

    Returns:
        tuple[str, str, str]: Raw key, display prefix, sha256 hex digest.

    """
    raw = "sk_" + secrets.token_urlsafe(32)
    prefix = raw[:_KEY_PREFIX_LEN]
    digest = hashlib.sha256(raw.encode()).hexdigest()
    return raw, prefix, digest


class ApiKeyService:
    """Manage API keys for an org. Raw keys are never stored or returned after creation."""

    def __init__(
        self,
        repo: ApiKeyRepository,
        org_repo: OrgRepository,
        membership_repo: MembershipRepository,
    ) -> None:
        self.repo = repo
        self.org_repo = org_repo
        self.membership_repo = membership_repo

    async def create(
        self,
        org_id: uuid.UUID,
        user_id: uuid.UUID,
        name: str,
        expires_at: Optional[datetime] = None,
    ) -> ApiKeyCreatedResponse:
        """Create a new API key and return the raw key once.

        Args:
            org_id (uuid.UUID): The org's UUID.
            user_id (uuid.UUID): The creating user — must be admin or owner.
            name (str): Human-readable label for the key.
            expires_at (datetime | None): Optional expiry timestamp.

        Raises:
            NotFoundError: If the org does not exist.
            ForbiddenError: If the user is not an admin or owner.

        Returns:
            ApiKeyCreatedResponse: Key metadata plus the raw key (shown once).

        """
        await self._assert_admin(org_id, user_id)

        raw_key, prefix, key_hash = _generate_key()
        key = ApiKey(
            org_id=org_id,
            created_by=user_id,
            name=name,
            key_prefix=prefix,
            key_hash=key_hash,
            expires_at=expires_at,
        )
        created = await self.repo.create(key)
        log.info("api_key.created", org_id=str(org_id), key_id=str(created.id))
        response = ApiKeyResponse.model_validate(created)
        return ApiKeyCreatedResponse(**response.model_dump(), raw_key=raw_key)

    async def list_keys(
        self, org_id: uuid.UUID, user_id: uuid.UUID
    ) -> list[ApiKeyResponse]:
        """Return all active API keys for an org.

        Args:
            org_id (uuid.UUID): The org's UUID.
            user_id (uuid.UUID): Requesting user — must be admin or owner.

        Raises:
            NotFoundError: If the org does not exist.
            ForbiddenError: If the user is not an admin or owner.

        Returns:
            list[ApiKeyResponse]: Active API keys (prefix + metadata, never raw key).

        """
        await self._assert_admin(org_id, user_id)
        keys = await self.repo.get_by_org(org_id)
        return [ApiKeyResponse.model_validate(k) for k in keys]

    async def revoke(
        self, org_id: uuid.UUID, user_id: uuid.UUID, key_id: uuid.UUID
    ) -> None:
        """Revoke (soft-delete) an API key.

        Args:
            org_id (uuid.UUID): The org's UUID.
            user_id (uuid.UUID): Requesting user — must be admin or owner.
            key_id (uuid.UUID): The API key UUID to revoke.

        Raises:
            NotFoundError: If the key does not exist or is already revoked.
            ForbiddenError: If the user is not an admin or owner.

        """
        await self._assert_admin(org_id, user_id)
        key = await self.repo.get_by_id_and_org(key_id, org_id)
        if not key:
            raise NotFoundError("ApiKey", key_id)
        await self.repo.soft_delete(key)
        log.info("api_key.revoked", org_id=str(org_id), key_id=str(key_id))

    async def verify(self, raw_key: str) -> Optional[ApiKey]:
        """Look up a key by its raw value for request authentication.

        Args:
            raw_key (str): The raw API key from the Authorization header.

        Returns:
            ApiKey | None: The matching active key, or None if not found/revoked.

        """
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        return await self.repo.get_by_hash(key_hash)

    async def _assert_admin(self, org_id: uuid.UUID, user_id: uuid.UUID) -> None:
        org = await self.org_repo.get_by_id(org_id)
        if not org:
            raise NotFoundError("Organisation", org_id)
        if not await self.membership_repo.user_has_role(user_id, org_id, Role.ADMIN):
            raise ForbiddenError("Only admins can manage API keys")
