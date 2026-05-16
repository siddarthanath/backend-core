"""OrgRepository and MembershipRepository — data access for orgs and memberships."""

# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Standard Library
import uuid

# Third Party
from sqlalchemy import and_, func, select

# Internal
from src.constants import MembershipStatus, Role
from src.models.org import Membership, Organisation
from src.models.user import UserProfile
from src.repositories.base import BaseRepository

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #

_ROLE_RANK: dict[Role, int] = {Role.OWNER: 3, Role.ADMIN: 2, Role.MEMBER: 1}


class OrgRepository(BaseRepository[Organisation]):
    """Repository for Organisation records."""

    model_class = Organisation

    async def get_by_slug(self, slug: str) -> Organisation | None:
        """Fetch a non-deleted org by its URL slug.

        Args:
            slug (str): The unique org slug.

        Returns:
            Organisation | None: The matching org, or None.

        """
        stmt = (
            select(Organisation)
            .where(Organisation.slug == slug)
            .where(self._not_deleted())
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_user_orgs(self, user_id: uuid.UUID) -> list[Organisation]:
        """Return all non-deleted orgs where the user is an active member.

        Args:
            user_id (uuid.UUID): The user's UUID.

        Returns:
            list[Organisation]: Active orgs the user belongs to.

        """
        stmt = (
            select(Organisation)
            .join(Membership, Membership.org_id == Organisation.id)
            .where(Membership.user_id == user_id)
            .where(Membership.status == MembershipStatus.ACTIVE)
            .where(self._not_deleted())
            .order_by(Organisation.created_at.asc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())


class MembershipRepository(BaseRepository[Membership]):
    """Repository for Membership records."""

    model_class = Membership

    async def get_membership(
        self,
        user_id: uuid.UUID,
        org_id: uuid.UUID,
    ) -> Membership | None:
        """Fetch a membership regardless of status.

        Args:
            user_id (uuid.UUID): The user's UUID.
            org_id (uuid.UUID): The org's UUID.

        Returns:
            Membership | None: The membership record, or None.

        """
        stmt = select(Membership).where(
            and_(Membership.user_id == user_id, Membership.org_id == org_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_org_members(self, org_id: uuid.UUID) -> list[tuple[Membership, str]]:
        """Return active memberships with member email for an org.

        Args:
            org_id (uuid.UUID): The org's UUID.

        Returns:
            list[tuple[Membership, str]]: Active memberships with email, ordered by creation date.

        """
        stmt = (
            select(Membership, UserProfile.email)
            .join(UserProfile, UserProfile.id == Membership.user_id)
            .where(Membership.org_id == org_id)
            .where(Membership.status == MembershipStatus.ACTIVE)
            .order_by(Membership.created_at.asc())
        )
        result = await self.session.execute(stmt)
        return [(row.Membership, row.email) for row in result.all()]

    async def count_owners(self, org_id: uuid.UUID) -> int:
        """Count active OWNER memberships in the org.

        Args:
            org_id (uuid.UUID): The org's UUID.

        Returns:
            int: Number of active owners.

        """
        stmt = (
            select(func.count())
            .select_from(Membership)
            .where(Membership.org_id == org_id)
            .where(Membership.role == Role.OWNER)
            .where(Membership.status == MembershipStatus.ACTIVE)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def get_user_memberships(self, user_id: uuid.UUID) -> list[Membership]:
        """Return all memberships for a user regardless of status.

        Args:
            user_id (uuid.UUID): The user's UUID.

        Returns:
            list[Membership]: All membership records for the user.

        """
        stmt = select(Membership).where(Membership.user_id == user_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def delete_all_for_user(self, user_id: uuid.UUID) -> None:
        """Hard-delete all membership records for a user.

        Args:
            user_id (uuid.UUID): The user's UUID.

        """
        memberships = await self.get_user_memberships(user_id)
        for m in memberships:
            await self.session.delete(m)
        await self.session.flush()

    async def user_has_role(
        self,
        user_id: uuid.UUID,
        org_id: uuid.UUID,
        minimum_role: Role,
    ) -> bool:
        """Return True if the user holds at least minimum_role in the org.

        Role hierarchy: owner (3) > admin (2) > member (1).
        Invited or suspended memberships always return False.

        Args:
            user_id (uuid.UUID): The user's UUID.
            org_id (uuid.UUID): The org's UUID.
            minimum_role (Role): The least-privileged role that passes.

        Returns:
            bool: Whether the user meets the role requirement.

        """
        membership = await self.get_membership(user_id, org_id)
        if not membership or membership.status != MembershipStatus.ACTIVE:
            return False
        return _ROLE_RANK[membership.role] >= _ROLE_RANK[minimum_role]
