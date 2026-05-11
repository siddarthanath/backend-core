"""Unit tests for OrgService — no database, all repositories mocked."""

# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Standard Library
import uuid
from unittest.mock import AsyncMock, MagicMock

# Third Party
import pytest

# Internal
from src.constants import MembershipStatus, Role
from src.core.exceptions.types import ConflictError, ForbiddenError, NotFoundError
from src.repositories.org import MembershipRepository, OrgRepository
from src.repositories.user import UserRepository
from src.services.org.service import OrgService

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #


def make_service(
    *,
    org_repo=None,
    membership_repo=None,
    user_repo=None,
):
    """Return an OrgService wired to mocked repositories."""
    org_repo = org_repo or AsyncMock(spec=OrgRepository)
    membership_repo = membership_repo or AsyncMock(spec=MembershipRepository)
    user_repo = user_repo or AsyncMock(spec=UserRepository)
    service = OrgService(
        org_repo=org_repo,
        membership_repo=membership_repo,
        user_repo=user_repo,
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


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_org_raises_conflict_on_duplicate_slug():
    service, org_repo, _, _ = make_service()
    org_repo.get_by_slug.return_value = make_org(slug="taken")

    with pytest.raises(ConflictError):
        await service.create_org(uuid.uuid4(), name="My Org", slug="taken")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_org_creates_owner_membership():
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


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_org_raises_not_found_for_unknown_org():
    service, org_repo, _, _ = make_service()
    org_repo.get_by_id.return_value = None

    with pytest.raises(NotFoundError):
        await service.get_org(uuid.uuid4(), uuid.uuid4())


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_org_raises_forbidden_if_not_member():
    service, org_repo, membership_repo, _ = make_service()
    org_repo.get_by_id.return_value = make_org()
    membership_repo.user_has_role.return_value = False

    with pytest.raises(ForbiddenError):
        await service.get_org(uuid.uuid4(), uuid.uuid4())


@pytest.mark.unit
@pytest.mark.asyncio
async def test_invite_member_raises_forbidden_if_inviter_not_admin():
    service, _, membership_repo, _ = make_service()
    membership_repo.user_has_role.return_value = False

    with pytest.raises(ForbiddenError):
        await service.invite_member(uuid.uuid4(), inviter_id=uuid.uuid4(), email="x@example.com")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_invite_member_raises_not_found_for_unknown_email():
    service, _, membership_repo, user_repo = make_service()
    membership_repo.user_has_role.return_value = True
    user_repo.get_by_email.return_value = None

    with pytest.raises(NotFoundError):
        await service.invite_member(uuid.uuid4(), inviter_id=uuid.uuid4(), email="nobody@example.com")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_invite_member_raises_conflict_if_already_member():
    service, _, membership_repo, user_repo = make_service()
    membership_repo.user_has_role.return_value = True
    user_repo.get_by_email.return_value = make_user()
    membership_repo.get_membership.return_value = make_membership()

    with pytest.raises(ConflictError):
        await service.invite_member(uuid.uuid4(), inviter_id=uuid.uuid4(), email="existing@example.com")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_invite_member_raises_forbidden_when_admin_assigns_owner_role():
    service, _, membership_repo, _ = make_service()
    # user_has_role returns True for ADMIN check, False for OWNER check
    membership_repo.user_has_role.side_effect = [True, False]

    with pytest.raises(ForbiddenError, match="owner"):
        await service.invite_member(uuid.uuid4(), inviter_id=uuid.uuid4(), email="x@example.com", role=Role.OWNER)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_accept_invite_raises_not_found_when_no_pending_invite():
    service, _, membership_repo, _ = make_service()
    membership_repo.get_membership.return_value = None

    with pytest.raises(NotFoundError):
        await service.accept_invite(uuid.uuid4(), uuid.uuid4())


@pytest.mark.unit
@pytest.mark.asyncio
async def test_accept_invite_raises_not_found_when_already_active():
    service, _, membership_repo, _ = make_service()
    membership_repo.get_membership.return_value = make_membership(status=MembershipStatus.ACTIVE)

    with pytest.raises(NotFoundError):
        await service.accept_invite(uuid.uuid4(), uuid.uuid4())


@pytest.mark.unit
@pytest.mark.asyncio
async def test_change_role_raises_forbidden_for_non_owner():
    service, _, membership_repo, _ = make_service()
    membership_repo.user_has_role.return_value = False

    with pytest.raises(ForbiddenError):
        await service.change_role(uuid.uuid4(), requester_id=uuid.uuid4(), target_user_id=uuid.uuid4(), new_role=Role.ADMIN)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_change_role_raises_not_found_for_non_member_target():
    service, _, membership_repo, _ = make_service()
    membership_repo.user_has_role.return_value = True
    membership_repo.get_membership.return_value = None

    with pytest.raises(NotFoundError):
        await service.change_role(uuid.uuid4(), requester_id=uuid.uuid4(), target_user_id=uuid.uuid4(), new_role=Role.ADMIN)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_remove_member_raises_forbidden_for_non_admin():
    service, _, membership_repo, _ = make_service()
    membership_repo.user_has_role.return_value = False

    with pytest.raises(ForbiddenError):
        await service.remove_member(uuid.uuid4(), requester_id=uuid.uuid4(), target_user_id=uuid.uuid4())


@pytest.mark.unit
@pytest.mark.asyncio
async def test_remove_member_raises_not_found_for_non_member_target():
    service, _, membership_repo, _ = make_service()
    membership_repo.user_has_role.return_value = True
    membership_repo.get_membership.return_value = None

    with pytest.raises(NotFoundError):
        await service.remove_member(uuid.uuid4(), requester_id=uuid.uuid4(), target_user_id=uuid.uuid4())


@pytest.mark.unit
@pytest.mark.asyncio
async def test_remove_member_raises_forbidden_when_admin_removes_owner():
    service, _, membership_repo, _ = make_service()
    # ADMIN check passes, OWNER check fails
    membership_repo.user_has_role.side_effect = [True, False]
    membership_repo.get_membership.return_value = make_membership(role=Role.OWNER)

    with pytest.raises(ForbiddenError, match="owner"):
        await service.remove_member(uuid.uuid4(), requester_id=uuid.uuid4(), target_user_id=uuid.uuid4())


@pytest.mark.unit
@pytest.mark.asyncio
async def test_remove_member_raises_forbidden_when_removing_last_owner():
    service, _, membership_repo, _ = make_service()
    membership_repo.user_has_role.return_value = True  # requester is owner
    membership_repo.get_membership.return_value = make_membership(role=Role.OWNER)
    membership_repo.count_owners.return_value = 1

    with pytest.raises(ForbiddenError, match="last owner"):
        await service.remove_member(uuid.uuid4(), requester_id=uuid.uuid4(), target_user_id=uuid.uuid4())
