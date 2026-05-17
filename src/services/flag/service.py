"""FeatureFlagService — org-scoped feature toggle evaluation and management."""

# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Standard Library
import uuid
from typing import Optional

# Internal
from src.constants import Role
from src.core.exceptions.types import ForbiddenError, NotFoundError
from src.models.flag import FeatureFlag
from src.repositories.flag import FlagRepository
from src.repositories.org import MembershipRepository, OrgRepository
from src.schemas.flag.responses import FeatureFlagResponse
from src.utils.logging import get_logger

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #

log = get_logger(__name__)


class FeatureFlagService:
    """Manage and evaluate feature flags scoped to an org."""

    def __init__(
        self,
        repo: FlagRepository,
        org_repo: OrgRepository,
        membership_repo: MembershipRepository,
    ) -> None:
        self.repo = repo
        self.org_repo = org_repo
        self.membership_repo = membership_repo

    async def get_flags(
        self, org_id: uuid.UUID, user_id: uuid.UUID
    ) -> list[FeatureFlagResponse]:
        """Return all feature flags for an org.

        Args:
            org_id (uuid.UUID): The org's UUID.
            user_id (uuid.UUID): Requesting user — must be a member.

        Raises:
            NotFoundError: If the org does not exist.
            ForbiddenError: If the user is not a member.

        Returns:
            list[FeatureFlagResponse]: All flags for the org.

        """
        await self._assert_org_and_member(org_id, user_id)
        flags = await self.repo.get_by_org(org_id)
        return [FeatureFlagResponse.model_validate(f) for f in flags]

    async def evaluate(
        self, org_id: uuid.UUID, user_id: uuid.UUID, key: str
    ) -> bool:
        """Evaluate a single flag for an org.

        Returns False if the flag does not exist — always conservative.

        Args:
            org_id (uuid.UUID): The org's UUID.
            user_id (uuid.UUID): Requesting user — must be a member.
            key (str): The flag key to evaluate.

        Raises:
            NotFoundError: If the org does not exist.
            ForbiddenError: If the user is not a member.

        Returns:
            bool: True if the flag exists and is enabled.

        """
        await self._assert_org_and_member(org_id, user_id)
        flag = await self.repo.get_by_org_and_key(org_id, key)
        return flag.enabled if flag else False

    async def upsert(
        self,
        org_id: uuid.UUID,
        user_id: uuid.UUID,
        key: str,
        enabled: bool,
        description: Optional[str] = None,
    ) -> FeatureFlagResponse:
        """Create or update a feature flag.

        Args:
            org_id (uuid.UUID): The org's UUID.
            user_id (uuid.UUID): Requesting user — must be admin or owner.
            key (str): The flag key (snake_case).
            enabled (bool): Whether the flag is enabled.
            description (str | None): Human-readable description.

        Raises:
            NotFoundError: If the org does not exist.
            ForbiddenError: If the user is not an admin or owner.

        Returns:
            FeatureFlagResponse: The created or updated flag.

        """
        await self._assert_org_and_admin(org_id, user_id)

        existing = await self.repo.get_by_org_and_key(org_id, key)
        if existing:
            updated = await self.repo.update(
                existing, enabled=enabled, description=description
            )
            return FeatureFlagResponse.model_validate(updated)

        flag = FeatureFlag(
            org_id=org_id,
            key=key,
            enabled=enabled,
            description=description,
        )
        created = await self.repo.create(flag)
        log.info("flag.upserted", org_id=str(org_id), key=key, enabled=enabled)
        return FeatureFlagResponse.model_validate(created)

    async def delete(
        self, org_id: uuid.UUID, user_id: uuid.UUID, flag_id: uuid.UUID
    ) -> None:
        """Delete a feature flag.

        Args:
            org_id (uuid.UUID): The org's UUID.
            user_id (uuid.UUID): Requesting user — must be admin or owner.
            flag_id (uuid.UUID): The flag UUID to delete.

        Raises:
            NotFoundError: If the flag does not exist for this org.
            ForbiddenError: If the user is not an admin or owner.

        """
        await self._assert_org_and_admin(org_id, user_id)
        flag = await self.repo.get_by_id(flag_id)
        if not flag or flag.org_id != org_id:
            raise NotFoundError("FeatureFlag", flag_id)
        await self.repo.hard_delete(flag)

    async def _assert_org_and_member(
        self, org_id: uuid.UUID, user_id: uuid.UUID
    ) -> None:
        org = await self.org_repo.get_by_id(org_id)
        if not org:
            raise NotFoundError("Organisation", org_id)
        if not await self.membership_repo.user_has_role(user_id, org_id, Role.MEMBER):
            raise ForbiddenError("You are not a member of this organisation")

    async def _assert_org_and_admin(
        self, org_id: uuid.UUID, user_id: uuid.UUID
    ) -> None:
        org = await self.org_repo.get_by_id(org_id)
        if not org:
            raise NotFoundError("Organisation", org_id)
        if not await self.membership_repo.user_has_role(user_id, org_id, Role.ADMIN):
            raise ForbiddenError("Only admins can manage feature flags")
