"""OrgService — org lifecycle: create, read, update, and member management."""

# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Standard Library
import uuid

# Third Party
from sqlalchemy.ext.asyncio import AsyncSession

# Internal
from src.constants import MembershipStatus, Role
from src.core.exceptions.types import ConflictError, ForbiddenError, NotFoundError
from src.models.org import Membership, Organisation
from src.repositories.org import MembershipRepository, OrgRepository
from src.repositories.user import UserRepository

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #


class OrgService:
    """Orchestrates org and membership operations. Raises typed exceptions, never HTTPException."""

    def __init__(self, session: AsyncSession) -> None:
        self.org_repo = OrgRepository(session)
        self.membership_repo = MembershipRepository(session)
        self.user_repo = UserRepository(session)

    async def create_org(
        self,
        user_id: uuid.UUID,
        name: str,
        slug: str,
        is_personal: bool = False,
    ) -> Organisation:
        """Create an org and make the creator an active OWNER.

        Args:
            user_id (uuid.UUID): The creating user's UUID.
            name (str): Display name for the org.
            slug (str): URL-safe unique identifier.
            is_personal (bool): True for personal workspaces.

        Raises:
            ConflictError: If slug is already taken.

        Returns:
            Organisation: The newly created org.

        """
        if await self.org_repo.get_by_slug(slug):
            raise ConflictError("Organisation", "slug", slug)

        org = await self.org_repo.create(Organisation(name=name, slug=slug, is_personal=is_personal))
        await self.membership_repo.create(
            Membership(
                user_id=user_id,
                org_id=org.id,
                role=Role.OWNER,
                status=MembershipStatus.ACTIVE,
            )
        )
        return org

    async def get_org(self, org_id: uuid.UUID, user_id: uuid.UUID) -> Organisation:
        """Return the org if the user is an active member.

        Args:
            org_id (uuid.UUID): The org's UUID.
            user_id (uuid.UUID): The requesting user's UUID.

        Raises:
            NotFoundError: If the org does not exist.
            ForbiddenError: If the user is not an active member.

        Returns:
            Organisation: The requested org.

        """
        org = await self.org_repo.get_by_id(org_id)
        if not org:
            raise NotFoundError("Organisation", org_id)
        if not await self.membership_repo.user_has_role(user_id, org_id, Role.MEMBER):
            raise ForbiddenError("You are not a member of this organisation")
        return org

    async def update_org(
        self,
        org_id: uuid.UUID,
        user_id: uuid.UUID,
        name: str | None = None,
    ) -> Organisation:
        """Update org fields. Requires admin or owner role.

        Args:
            org_id (uuid.UUID): The org's UUID.
            user_id (uuid.UUID): The requesting user's UUID.
            name (str | None): New display name, or None to leave unchanged.

        Raises:
            NotFoundError: If the org does not exist.
            ForbiddenError: If the user is not an admin or owner.

        Returns:
            Organisation: The updated org.

        """
        org = await self.org_repo.get_by_id(org_id)
        if not org:
            raise NotFoundError("Organisation", org_id)
        if not await self.membership_repo.user_has_role(user_id, org_id, Role.ADMIN):
            raise ForbiddenError("Only admins can update org details")
        updates: dict[str, object] = {}
        if name is not None:
            updates["name"] = name
        return await self.org_repo.update(org, **updates)

    async def invite_member(
        self,
        org_id: uuid.UUID,
        inviter_id: uuid.UUID,
        email: str,
        role: Role = Role.MEMBER,
    ) -> Membership:
        """Invite an existing user to the org by email.

        The invitee must already have an account — this creates a Membership with
        INVITED status. Full pending-invite support (for users without accounts)
        requires the email service wired in Round 5+.

        Args:
            org_id (uuid.UUID): The org's UUID.
            inviter_id (uuid.UUID): The inviting user's UUID.
            email (str): Email of the user to invite.
            role (Role): Role to assign on acceptance.

        Raises:
            ForbiddenError: If the inviter is not an admin or owner.
            NotFoundError: If no user with that email exists.
            ConflictError: If the user is already a member.

        Returns:
            Membership: The newly created membership (status=INVITED).

        """
        if not await self.membership_repo.user_has_role(inviter_id, org_id, Role.ADMIN):
            raise ForbiddenError("Only admins can invite members")

        invitee = await self.user_repo.get_by_email(email)
        if not invitee:
            raise NotFoundError("User", email)

        existing = await self.membership_repo.get_membership(invitee.id, org_id)
        if existing:
            raise ConflictError("Membership", "user", email)

        return await self.membership_repo.create(
            Membership(
                user_id=invitee.id,
                org_id=org_id,
                role=role,
                status=MembershipStatus.INVITED,
                invited_by=inviter_id,
            )
        )

    async def accept_invite(self, org_id: uuid.UUID, user_id: uuid.UUID) -> Membership:
        """Accept a pending invite, setting membership status to ACTIVE.

        Args:
            org_id (uuid.UUID): The org's UUID.
            user_id (uuid.UUID): The accepting user's UUID.

        Raises:
            NotFoundError: If no pending invite exists for this user.

        Returns:
            Membership: The updated membership (status=ACTIVE).

        """
        membership = await self.membership_repo.get_membership(user_id, org_id)
        if not membership or membership.status != MembershipStatus.INVITED:
            raise NotFoundError("Invite", org_id)
        return await self.membership_repo.update(membership, status=MembershipStatus.ACTIVE)

    async def change_role(
        self,
        org_id: uuid.UUID,
        requester_id: uuid.UUID,
        target_user_id: uuid.UUID,
        new_role: Role,
    ) -> Membership:
        """Change a member's role. Only owners can do this.

        Args:
            org_id (uuid.UUID): The org's UUID.
            requester_id (uuid.UUID): The requesting user's UUID.
            target_user_id (uuid.UUID): The member whose role is being changed.
            new_role (Role): The new role to assign.

        Raises:
            ForbiddenError: If the requester is not an owner.
            NotFoundError: If the target user is not a member.

        Returns:
            Membership: The updated membership.

        """
        if not await self.membership_repo.user_has_role(requester_id, org_id, Role.OWNER):
            raise ForbiddenError("Only owners can change member roles")

        membership = await self.membership_repo.get_membership(target_user_id, org_id)
        if not membership:
            raise NotFoundError("Membership", target_user_id)

        return await self.membership_repo.update(membership, role=new_role)

    async def remove_member(
        self,
        org_id: uuid.UUID,
        requester_id: uuid.UUID,
        target_user_id: uuid.UUID,
    ) -> None:
        """Hard-delete a membership. Requires admin or owner role.

        Args:
            org_id (uuid.UUID): The org's UUID.
            requester_id (uuid.UUID): The requesting user's UUID.
            target_user_id (uuid.UUID): The member to remove.

        Raises:
            ForbiddenError: If the requester is not an admin or owner.
            NotFoundError: If the target user is not a member.

        """
        if not await self.membership_repo.user_has_role(requester_id, org_id, Role.ADMIN):
            raise ForbiddenError("Only admins can remove members")

        membership = await self.membership_repo.get_membership(target_user_id, org_id)
        if not membership:
            raise NotFoundError("Membership", target_user_id)

        await self.membership_repo.hard_delete(membership)
