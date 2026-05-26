"""Unit tests for OrgService — no database, all repositories mocked."""

# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Standard Library
import uuid
from unittest.mock import AsyncMock, MagicMock

# Third-Party Library
import pytest

# Private Library
from src.constants import MembershipStatus, Role
from src.core.exceptions.types import AppValidationError, ConflictError, ForbiddenError, NotFoundError
from src.repositories.org import MembershipRepository, OrgRepository
from src.repositories.user import UserRepository
from src.services.org.service import OrgService

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #


def make_service(
    *,
    org_repo=None,
    membership_repo=None,
    user_repo=None,
    email_service=None,
):
    """Return an OrgService wired to mocked repositories."""
    org_repo = org_repo or AsyncMock(spec=OrgRepository)
    membership_repo = membership_repo or AsyncMock(spec=MembershipRepository)
    user_repo = user_repo or AsyncMock(spec=UserRepository)
    email_service = email_service or AsyncMock()
    service = OrgService(
        org_repo=org_repo,
        membership_repo=membership_repo,
        user_repo=user_repo,
        email_service=email_service,
    )
    return service, org_repo, membership_repo, user_repo


def make_org(**kwargs):
    org = MagicMock()
    org.id = kwargs.get("id", uuid.uuid4())
    org.name = kwargs.get("name", "Test Org")
    org.slug = kwargs.get("slug", "test-org")
    return org


def make_membership(**kwargs):
    m = MagicMock()
    m.id = kwargs.get("id", uuid.uuid4())
    m.user_id = kwargs.get("user_id", uuid.uuid4())
    m.org_id = kwargs.get("org_id", uuid.uuid4())
    m.role = kwargs.get("role", Role.MEMBER)
    m.status = kwargs.get("status", MembershipStatus.ACTIVE)
    return m


def make_user(**kwargs):
    u = MagicMock()
    u.id = kwargs.get("id", uuid.uuid4())
    u.email = kwargs.get("email", "user@example.com")
    return u


class TestCreateOrg:
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_raises_conflict_on_duplicate_slug(self) -> None:
        service, org_repo, _, _ = make_service()
        org_repo.get_by_slug.return_value = make_org(slug="taken")

        with pytest.raises(ConflictError):
            await service.create_org(uuid.uuid4(), name="My Org", slug="taken")

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_creates_owner_membership(self) -> None:
        service, org_repo, membership_repo, _ = make_service()
        org = make_org()
        org_repo.get_by_slug.return_value = None
        org_repo.create.return_value = org
        membership_repo.create.return_value = make_membership()

        await service.create_org(uuid.uuid4(), name="My Org", slug="new-org")

        membership_repo.create.assert_awaited_once()
        created = membership_repo.create.call_args[0][0]
        assert created.role == Role.OWNER
        assert created.status == MembershipStatus.ACTIVE


class TestGetOrCreatePersonal:
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_returns_existing_org(self) -> None:
        service, org_repo, _, _ = make_service()
        user_id = uuid.uuid4()
        existing = make_org(slug=str(user_id))
        org_repo.get_by_slug.return_value = existing

        result = await service.get_or_create_personal(user_id, email="u@example.com")

        assert result is existing
        org_repo.create.assert_not_awaited()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_creates_personal_org_on_first_call(self) -> None:
        service, org_repo, membership_repo, _ = make_service()
        user_id = uuid.uuid4()
        org_repo.get_by_slug.return_value = None
        new_org = make_org(slug=str(user_id))
        org_repo.create.return_value = new_org
        membership_repo.create.return_value = make_membership()

        result = await service.get_or_create_personal(user_id, email="u@example.com")

        assert result is new_org

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_handles_race_condition_on_concurrent_first_login(self) -> None:
        # Simulates two concurrent first-logins: both pass the initial get_by_slug check.
        # The race winner commits before the loser's create_org slug check runs, so
        # create_org raises ConflictError. get_or_create_personal catches it and re-fetches.
        # get_by_slug call sequence: None (initial) → org (inside create_org) → org (re-fetch).
        service, org_repo, _, _ = make_service()
        user_id = uuid.uuid4()
        org = make_org(slug=str(user_id))

        org_repo.get_by_slug.side_effect = [None, org, org]

        result = await service.get_or_create_personal(user_id, email="u@example.com")

        assert result is org


class TestGetOrg:
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_raises_not_found_for_unknown_org(self) -> None:
        service, org_repo, _, _ = make_service()
        org_repo.get_by_id.return_value = None

        with pytest.raises(NotFoundError):
            await service.get_org(uuid.uuid4(), uuid.uuid4())

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_raises_forbidden_if_not_member(self) -> None:
        service, org_repo, membership_repo, _ = make_service()
        org_repo.get_by_id.return_value = make_org()
        membership_repo.user_has_role.return_value = False

        with pytest.raises(ForbiddenError):
            await service.get_org(uuid.uuid4(), uuid.uuid4())


class TestInviteMember:
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_raises_forbidden_if_inviter_not_admin(self) -> None:
        service, _, membership_repo, _ = make_service()
        membership_repo.user_has_role.return_value = False

        with pytest.raises(ForbiddenError):
            await service.invite_member(
                uuid.uuid4(), inviter_id=uuid.uuid4(), email="x@example.com"
            )

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_raises_not_found_for_unknown_email(self) -> None:
        service, _, membership_repo, user_repo = make_service()
        membership_repo.user_has_role.return_value = True
        user_repo.get_by_email.return_value = None

        with pytest.raises(NotFoundError):
            await service.invite_member(
                uuid.uuid4(), inviter_id=uuid.uuid4(), email="nobody@example.com"
            )

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_raises_conflict_if_already_member(self) -> None:
        service, _, membership_repo, user_repo = make_service()
        membership_repo.user_has_role.return_value = True
        user_repo.get_by_email.return_value = make_user()
        membership_repo.get_membership.return_value = make_membership()

        with pytest.raises(ConflictError):
            await service.invite_member(
                uuid.uuid4(), inviter_id=uuid.uuid4(), email="existing@example.com"
            )

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_raises_forbidden_when_admin_assigns_owner_role(self) -> None:
        service, _, membership_repo, _ = make_service()
        # user_has_role returns True for ADMIN check, False for OWNER check
        membership_repo.user_has_role.side_effect = [True, False]

        with pytest.raises(ForbiddenError, match="owner"):
            await service.invite_member(
                uuid.uuid4(),
                inviter_id=uuid.uuid4(),
                email="x@example.com",
                role=Role.OWNER,
            )


class TestAcceptInvite:
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_raises_not_found_when_no_pending_invite(self) -> None:
        service, _, membership_repo, _ = make_service()
        membership_repo.get_membership.return_value = None

        with pytest.raises(NotFoundError):
            await service.accept_invite(uuid.uuid4(), uuid.uuid4())

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_raises_not_found_when_already_active(self) -> None:
        service, _, membership_repo, _ = make_service()
        membership_repo.get_membership.return_value = make_membership(
            status=MembershipStatus.ACTIVE
        )

        with pytest.raises(NotFoundError):
            await service.accept_invite(uuid.uuid4(), uuid.uuid4())


class TestChangeRole:
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_raises_forbidden_for_non_owner(self) -> None:
        service, _, membership_repo, _ = make_service()
        membership_repo.user_has_role.return_value = False

        with pytest.raises(ForbiddenError):
            await service.change_role(
                uuid.uuid4(),
                requester_id=uuid.uuid4(),
                target_user_id=uuid.uuid4(),
                new_role=Role.ADMIN,
            )

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_raises_not_found_for_non_member_target(self) -> None:
        service, _, membership_repo, _ = make_service()
        membership_repo.user_has_role.return_value = True
        membership_repo.get_membership.return_value = None

        with pytest.raises(NotFoundError):
            await service.change_role(
                uuid.uuid4(),
                requester_id=uuid.uuid4(),
                target_user_id=uuid.uuid4(),
                new_role=Role.ADMIN,
            )


class TestRemoveMember:
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_raises_forbidden_for_non_admin(self) -> None:
        service, _, membership_repo, _ = make_service()
        membership_repo.user_has_role.return_value = False

        with pytest.raises(ForbiddenError):
            await service.remove_member(
                uuid.uuid4(), requester_id=uuid.uuid4(), target_user_id=uuid.uuid4()
            )

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_raises_not_found_for_non_member_target(self) -> None:
        service, _, membership_repo, _ = make_service()
        membership_repo.user_has_role.return_value = True
        membership_repo.get_membership.return_value = None

        with pytest.raises(NotFoundError):
            await service.remove_member(
                uuid.uuid4(), requester_id=uuid.uuid4(), target_user_id=uuid.uuid4()
            )

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_raises_forbidden_when_admin_removes_owner(self) -> None:
        service, _, membership_repo, _ = make_service()
        # ADMIN check passes, OWNER check fails
        membership_repo.user_has_role.side_effect = [True, False]
        membership_repo.get_membership.return_value = make_membership(role=Role.OWNER)

        with pytest.raises(ForbiddenError, match="owner"):
            await service.remove_member(
                uuid.uuid4(), requester_id=uuid.uuid4(), target_user_id=uuid.uuid4()
            )

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_raises_forbidden_when_removing_last_owner(self) -> None:
        service, _, membership_repo, _ = make_service()
        membership_repo.user_has_role.return_value = True  # requester is owner
        membership_repo.get_membership.return_value = make_membership(role=Role.OWNER)
        membership_repo.count_owners.return_value = 1

        with pytest.raises(ForbiddenError, match="last owner"):
            await service.remove_member(
                uuid.uuid4(), requester_id=uuid.uuid4(), target_user_id=uuid.uuid4()
            )


class TestCleanupForDeletedUser:
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_raises_validation_error_when_sole_owner_of_shared_org(self) -> None:
        service, org_repo, membership_repo, _ = make_service()
        user_id = uuid.uuid4()
        org_id = uuid.uuid4()
        membership = make_membership(user_id=user_id, org_id=org_id, role=Role.OWNER)

        membership_repo.get_user_memberships.return_value = [membership]
        membership_repo.count_owners.return_value = 1
        membership_repo.count_active_members.return_value = 2  # owner + 1 other member

        with pytest.raises(AppValidationError):
            await service.cleanup_for_deleted_user(user_id)

        org_repo.hard_delete.assert_not_awaited()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_hard_deletes_sole_owned_org(self) -> None:
        service, org_repo, membership_repo, _ = make_service()
        user_id = uuid.uuid4()
        org_id = uuid.uuid4()
        org = make_org(id=org_id)
        membership = make_membership(user_id=user_id, org_id=org_id, role=Role.OWNER)

        membership_repo.get_user_memberships.return_value = [membership]
        membership_repo.count_owners.return_value = 1
        membership_repo.count_active_members.return_value = 1  # only the owner
        org_repo.get_by_id.return_value = org

        await service.cleanup_for_deleted_user(user_id)

        org_repo.hard_delete.assert_awaited_once_with(org)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_does_not_delete_multi_owner_org(self) -> None:
        service, org_repo, membership_repo, _ = make_service()
        user_id = uuid.uuid4()
        org_id = uuid.uuid4()
        membership = make_membership(user_id=user_id, org_id=org_id, role=Role.OWNER)

        membership_repo.get_user_memberships.return_value = [membership]
        membership_repo.count_owners.return_value = 2

        await service.cleanup_for_deleted_user(user_id)

        org_repo.hard_delete.assert_not_awaited()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_does_not_delete_non_owner_org(self) -> None:
        service, org_repo, membership_repo, _ = make_service()
        user_id = uuid.uuid4()
        org_id = uuid.uuid4()
        membership = make_membership(user_id=user_id, org_id=org_id, role=Role.MEMBER)

        membership_repo.get_user_memberships.return_value = [membership]

        await service.cleanup_for_deleted_user(user_id)

        org_repo.hard_delete.assert_not_awaited()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_no_op_when_no_memberships(self) -> None:
        service, org_repo, membership_repo, _ = make_service()
        membership_repo.get_user_memberships.return_value = []

        await service.cleanup_for_deleted_user(uuid.uuid4())

        org_repo.hard_delete.assert_not_awaited()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_deletes_non_owner_memberships(self) -> None:
        service, org_repo, membership_repo, _ = make_service()
        user_id = uuid.uuid4()
        membership = make_membership(user_id=user_id, role=Role.MEMBER)

        membership_repo.get_user_memberships.return_value = [membership]

        await service.cleanup_for_deleted_user(user_id)

        org_repo.hard_delete.assert_not_awaited()
        membership_repo.delete_all_for_user.assert_awaited_once_with(user_id)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_deletes_all_memberships_after_org_cleanup(self) -> None:
        service, org_repo, membership_repo, _ = make_service()
        user_id = uuid.uuid4()
        org_id = uuid.uuid4()
        org = make_org(id=org_id)
        owner_membership = make_membership(
            user_id=user_id, org_id=org_id, role=Role.OWNER
        )

        membership_repo.get_user_memberships.return_value = [owner_membership]
        membership_repo.count_owners.return_value = 1
        membership_repo.count_active_members.return_value = 1  # only the owner
        org_repo.get_by_id.return_value = org

        await service.cleanup_for_deleted_user(user_id)

        org_repo.hard_delete.assert_awaited_once_with(org)
        membership_repo.delete_all_for_user.assert_awaited_once_with(user_id)


class TestTransferOwnership:
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_raises_forbidden_for_non_owner(self) -> None:
        service, _, membership_repo, _ = make_service()
        membership_repo.user_has_role.return_value = False

        with pytest.raises(ForbiddenError):
            await service.transfer_ownership(
                uuid.uuid4(), requester_id=uuid.uuid4(), new_owner_id=uuid.uuid4()
            )

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_raises_validation_error_when_transferring_to_self(self) -> None:
        service, _, membership_repo, _ = make_service()
        membership_repo.user_has_role.return_value = True
        user_id = uuid.uuid4()

        with pytest.raises(AppValidationError):
            await service.transfer_ownership(
                uuid.uuid4(), requester_id=user_id, new_owner_id=user_id
            )

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_raises_not_found_when_target_not_a_member(self) -> None:
        service, _, membership_repo, _ = make_service()
        membership_repo.user_has_role.return_value = True
        membership_repo.get_membership.return_value = None

        with pytest.raises(NotFoundError):
            await service.transfer_ownership(
                uuid.uuid4(), requester_id=uuid.uuid4(), new_owner_id=uuid.uuid4()
            )

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_raises_not_found_when_target_is_invited(self) -> None:
        service, _, membership_repo, _ = make_service()
        membership_repo.user_has_role.return_value = True
        membership_repo.get_membership.return_value = make_membership(
            status=MembershipStatus.INVITED
        )

        with pytest.raises(NotFoundError):
            await service.transfer_ownership(
                uuid.uuid4(), requester_id=uuid.uuid4(), new_owner_id=uuid.uuid4()
            )

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_promotes_new_owner_and_demotes_requester(self) -> None:
        service, _, membership_repo, _ = make_service()
        requester_id = uuid.uuid4()
        new_owner_id = uuid.uuid4()
        new_owner_membership = make_membership(
            user_id=new_owner_id, role=Role.MEMBER, status=MembershipStatus.ACTIVE
        )
        requester_membership = make_membership(
            user_id=requester_id, role=Role.OWNER, status=MembershipStatus.ACTIVE
        )

        membership_repo.user_has_role.return_value = True
        # First get_membership: new owner. Second: requester (post-promotion lookup).
        membership_repo.get_membership.side_effect = [
            new_owner_membership,
            requester_membership,
        ]
        membership_repo.update.return_value = new_owner_membership

        result = await service.transfer_ownership(
            uuid.uuid4(), requester_id=requester_id, new_owner_id=new_owner_id
        )

        assert result is new_owner_membership
        first_update = membership_repo.update.call_args_list[0]
        assert first_update[1]["role"] == Role.OWNER
        second_update = membership_repo.update.call_args_list[1]
        assert second_update[1]["role"] == Role.ADMIN
