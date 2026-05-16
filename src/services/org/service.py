"""OrgService — org lifecycle: create, read, update, and member management."""

# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Standard Library
import uuid

# Internal
from src.constants import MembershipStatus, Role
from src.core.exceptions.types import ConflictError, ForbiddenError, NotFoundError
from src.models.org import Membership, Organisation
from src.repositories.org import MembershipRepository, OrgRepository
from src.repositories.user import UserRepository
from src.schemas.org.responses import MemberResponse

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #


class OrgService:
    """Orchestrates org and membership operations. Raises typed exceptions, never HTTPException."""

    def __init__(
        self,
        org_repo: OrgRepository,
        membership_repo: MembershipRepository,
        user_repo: UserRepository,
    ) -> None:
        self.org_repo = org_repo
        self.membership_repo = membership_repo
        self.user_repo = user_repo

    async def get_or_create_personal(self, user_id: uuid.UUID, email: str) -> Organisation:
        """Return the user's personal org, creating it on first call.

        Idempotent — safe to call on every login. The org slug is derived from
        the user_id so it is guaranteed unique without a slug-check round-trip.

        B2B note: personal orgs are invisible in B2B products. In B2B, remove this
        call from get_me and expose POST /orgs so teams create named workspaces.

        Args:
            user_id (uuid.UUID): The authenticated user's UUID.
            email (str): Used as the org display name (never shown in B2C UI).

        Returns:
            Organisation: The personal org (existing or newly created).

        """
        # Subscription row is NOT created here — upsert_free in BillingService handles
        # it lazily on first billing call. Injecting SubscriptionRepository here would
        # couple two unrelated services for zero practical benefit.
        slug = str(user_id)
        existing = await self.org_repo.get_by_slug(slug)
        if existing:
            return existing
        return await self.create_org(user_id, name=email, slug=slug, is_personal=True)

    async def list_my_orgs(self, user_id: uuid.UUID) -> list[Organisation]:
        """Return all orgs the user is an active member of.

        Args:
            user_id (uuid.UUID): The requesting user's UUID.

        Returns:
            list[Organisation]: Active orgs for this user.

        """
        return await self.org_repo.get_user_orgs(user_id)

    async def list_members(self, org_id: uuid.UUID, user_id: uuid.UUID) -> list[MemberResponse]:
        """Return active members of an org with email. User must be a member.

        Args:
            org_id (uuid.UUID): The org's UUID.
            user_id (uuid.UUID): The requesting user's UUID.

        Raises:
            NotFoundError: If the org does not exist.
            ForbiddenError: If the user is not a member.

        Returns:
            list[MemberResponse]: Active memberships with email for this org.

        """
        await self.get_org(org_id, user_id)
        rows = await self.membership_repo.get_org_members(org_id)
        return [
            MemberResponse.model_validate(membership, update={"email": email})
            for membership, email in rows
        ]

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
        if role == Role.OWNER and not await self.membership_repo.user_has_role(inviter_id, org_id, Role.OWNER):
            raise ForbiddenError("Only owners can assign the owner role")

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

    async def cleanup_for_deleted_user(self, user_id: uuid.UUID) -> None:
        """Hard-delete orgs where this user is the sole owner.

        Called during account deletion before the user profile is removed.
        Subscriptions and memberships for deleted orgs cascade at the DB level.

        Args:
            user_id (uuid.UUID): The user being deleted.

        """
        memberships = await self.membership_repo.get_user_memberships(user_id)
        for membership in memberships:
            if membership.role == Role.OWNER:
                if await self.membership_repo.count_owners(membership.org_id) == 1:
                    org = await self.org_repo.get_by_id(membership.org_id)
                    if org:
                        await self.org_repo.hard_delete(org)

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

        if membership.role == Role.OWNER:
            if not await self.membership_repo.user_has_role(requester_id, org_id, Role.OWNER):
                raise ForbiddenError("Only owners can remove other owners")
            if await self.membership_repo.count_owners(org_id) <= 1:
                raise ForbiddenError("Cannot remove the last owner of an organisation")

        await self.membership_repo.hard_delete(membership)
