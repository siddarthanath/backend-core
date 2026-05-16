"""Unit tests for FeatureFlagService — no database, all repositories mocked."""

# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Standard Library
import uuid
from unittest.mock import AsyncMock, MagicMock

# Third Party
import pytest

# Internal
from src.core.exceptions.types import ForbiddenError, NotFoundError
from src.repositories.flag import FlagRepository
from src.repositories.org import MembershipRepository, OrgRepository
from src.services.flag.service import FeatureFlagService

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #


def make_service(*, repo=None, org_repo=None, membership_repo=None):
    repo = repo or AsyncMock(spec=FlagRepository)
    org_repo = org_repo or AsyncMock(spec=OrgRepository)
    membership_repo = membership_repo or AsyncMock(spec=MembershipRepository)
    return FeatureFlagService(repo=repo, org_repo=org_repo, membership_repo=membership_repo), repo, org_repo, membership_repo


def make_flag(**kwargs):
    flag = MagicMock()
    flag.id = kwargs.get("id", uuid.uuid4())
    flag.org_id = kwargs.get("org_id", uuid.uuid4())
    flag.key = kwargs.get("key", "test_flag")
    flag.enabled = kwargs.get("enabled", False)
    flag.description = kwargs.get("description", None)
    flag.created_at = kwargs.get("created_at", None)
    flag.updated_at = kwargs.get("updated_at", None)
    return flag


def _with_member_access(org_repo, membership_repo, org_id):
    org_repo.get_by_id.return_value = MagicMock(id=org_id)
    membership_repo.user_has_role.return_value = True


@pytest.mark.asyncio
async def test_get_flags_returns_all_org_flags():
    svc, repo, org_repo, membership_repo = make_service()
    org_id = uuid.uuid4()
    _with_member_access(org_repo, membership_repo, org_id)
    flags = [make_flag(org_id=org_id, key="flag_a"), make_flag(org_id=org_id, key="flag_b")]
    repo.get_by_org.return_value = flags

    result = await svc.get_flags(org_id, uuid.uuid4())
    assert len(result) == 2
    assert result[0].key == "flag_a"


@pytest.mark.asyncio
async def test_get_flags_raises_forbidden_for_non_member():
    svc, _, org_repo, membership_repo = make_service()
    org_repo.get_by_id.return_value = MagicMock()
    membership_repo.user_has_role.return_value = False

    with pytest.raises(ForbiddenError):
        await svc.get_flags(uuid.uuid4(), uuid.uuid4())


@pytest.mark.asyncio
async def test_evaluate_returns_true_when_flag_enabled():
    svc, repo, org_repo, membership_repo = make_service()
    org_id = uuid.uuid4()
    _with_member_access(org_repo, membership_repo, org_id)
    repo.get_by_org_and_key.return_value = make_flag(enabled=True)

    result = await svc.evaluate(org_id, uuid.uuid4(), "my_flag")
    assert result is True


@pytest.mark.asyncio
async def test_evaluate_returns_false_when_flag_disabled():
    svc, repo, org_repo, membership_repo = make_service()
    org_id = uuid.uuid4()
    _with_member_access(org_repo, membership_repo, org_id)
    repo.get_by_org_and_key.return_value = make_flag(enabled=False)

    result = await svc.evaluate(org_id, uuid.uuid4(), "my_flag")
    assert result is False


@pytest.mark.asyncio
async def test_evaluate_returns_false_when_flag_missing():
    """Missing flag is conservative — defaults to False."""
    svc, repo, org_repo, membership_repo = make_service()
    org_id = uuid.uuid4()
    _with_member_access(org_repo, membership_repo, org_id)
    repo.get_by_org_and_key.return_value = None

    result = await svc.evaluate(org_id, uuid.uuid4(), "nonexistent")
    assert result is False


@pytest.mark.asyncio
async def test_upsert_creates_new_flag():
    svc, repo, org_repo, membership_repo = make_service()
    org_id = uuid.uuid4()
    _with_member_access(org_repo, membership_repo, org_id)
    repo.get_by_org_and_key.return_value = None
    new_flag = make_flag(org_id=org_id, key="new_flag", enabled=True)
    repo.create.return_value = new_flag

    result = await svc.upsert(org_id, uuid.uuid4(), key="new_flag", enabled=True)
    repo.create.assert_called_once()
    assert result.key == "new_flag"
    assert result.enabled is True


@pytest.mark.asyncio
async def test_upsert_updates_existing_flag():
    svc, repo, org_repo, membership_repo = make_service()
    org_id = uuid.uuid4()
    _with_member_access(org_repo, membership_repo, org_id)
    existing = make_flag(org_id=org_id, key="existing_flag", enabled=False)
    repo.get_by_org_and_key.return_value = existing
    updated = make_flag(org_id=org_id, key="existing_flag", enabled=True)
    repo.update.return_value = updated

    result = await svc.upsert(org_id, uuid.uuid4(), key="existing_flag", enabled=True)
    repo.update.assert_called_once()
    repo.create.assert_not_called()
    assert result.enabled is True


@pytest.mark.asyncio
async def test_upsert_raises_forbidden_for_non_admin():
    svc, _, org_repo, membership_repo = make_service()
    org_repo.get_by_id.return_value = MagicMock()
    membership_repo.user_has_role.return_value = False

    with pytest.raises(ForbiddenError):
        await svc.upsert(uuid.uuid4(), uuid.uuid4(), key="flag", enabled=True)


@pytest.mark.asyncio
async def test_delete_removes_flag():
    svc, repo, org_repo, membership_repo = make_service()
    org_id = uuid.uuid4()
    _with_member_access(org_repo, membership_repo, org_id)
    flag = make_flag(org_id=org_id)
    repo.get_by_id.return_value = flag

    await svc.delete(org_id, uuid.uuid4(), flag.id)
    repo.hard_delete.assert_called_once_with(flag)


@pytest.mark.asyncio
async def test_delete_raises_not_found_when_flag_belongs_to_other_org():
    svc, repo, org_repo, membership_repo = make_service()
    org_id = uuid.uuid4()
    _with_member_access(org_repo, membership_repo, org_id)
    flag = make_flag(org_id=uuid.uuid4())  # different org
    repo.get_by_id.return_value = flag

    with pytest.raises(NotFoundError):
        await svc.delete(org_id, uuid.uuid4(), flag.id)
