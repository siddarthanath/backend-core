"""Unit tests for ApiKeyService — no database, all repositories mocked."""

# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Standard Library
import hashlib
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

# Third Party
import pytest

# Internal
from src.core.exceptions.types import ForbiddenError, NotFoundError
from src.repositories.api_key import ApiKeyRepository
from src.repositories.org import MembershipRepository, OrgRepository
from src.services.api_key.service import ApiKeyService, _generate_key

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #


def make_service(*, repo=None, org_repo=None, membership_repo=None):
    repo = repo or AsyncMock(spec=ApiKeyRepository)
    org_repo = org_repo or AsyncMock(spec=OrgRepository)
    membership_repo = membership_repo or AsyncMock(spec=MembershipRepository)
    return ApiKeyService(repo=repo, org_repo=org_repo, membership_repo=membership_repo), repo, org_repo, membership_repo


def make_key(**kwargs):
    key = MagicMock()
    key.id = kwargs.get("id", uuid.uuid4())
    key.org_id = kwargs.get("org_id", uuid.uuid4())
    key.created_by = kwargs.get("created_by", None)
    key.name = kwargs.get("name", "CI Pipeline")
    key.key_prefix = kwargs.get("key_prefix", "sk_testprefi")
    key.key_hash = kwargs.get("key_hash", "fakehash")
    key.last_used_at = kwargs.get("last_used_at", None)
    key.expires_at = kwargs.get("expires_at", None)
    key.created_at = kwargs.get("created_at", datetime.now(timezone.utc))
    key.updated_at = kwargs.get("updated_at", datetime.now(timezone.utc))
    return key


def _with_admin_access(org_repo, membership_repo, org_id):
    org_repo.get_by_id.return_value = MagicMock(id=org_id)
    membership_repo.user_has_role.return_value = True


def test_generate_key_format():
    raw, prefix, digest = _generate_key()
    assert raw.startswith("sk_")
    assert prefix == raw[:11]
    assert digest == hashlib.sha256(raw.encode()).hexdigest()


def test_generate_key_is_unique():
    keys = {_generate_key()[0] for _ in range(100)}
    assert len(keys) == 100


@pytest.mark.asyncio
async def test_create_returns_raw_key_once():
    svc, repo, org_repo, membership_repo = make_service()
    org_id = uuid.uuid4()
    user_id = uuid.uuid4()
    _with_admin_access(org_repo, membership_repo, org_id)
    stored = make_key(org_id=org_id, created_by=user_id, name="Deploy Key")
    repo.create.return_value = stored

    result = await svc.create(org_id, user_id, name="Deploy Key")

    assert result.raw_key.startswith("sk_")
    assert result.name == "Deploy Key"
    repo.create.assert_called_once()


@pytest.mark.asyncio
async def test_create_raises_forbidden_for_non_admin():
    svc, _, org_repo, membership_repo = make_service()
    org_repo.get_by_id.return_value = MagicMock()
    membership_repo.user_has_role.return_value = False

    with pytest.raises(ForbiddenError):
        await svc.create(uuid.uuid4(), uuid.uuid4(), name="key")


@pytest.mark.asyncio
async def test_create_raises_not_found_for_unknown_org():
    svc, _, org_repo, _ = make_service()
    org_repo.get_by_id.return_value = None

    with pytest.raises(NotFoundError):
        await svc.create(uuid.uuid4(), uuid.uuid4(), name="key")


@pytest.mark.asyncio
async def test_list_keys_returns_metadata_without_raw_key():
    svc, repo, org_repo, membership_repo = make_service()
    org_id = uuid.uuid4()
    _with_admin_access(org_repo, membership_repo, org_id)
    repo.get_by_org.return_value = [make_key(org_id=org_id), make_key(org_id=org_id)]

    result = await svc.list_keys(org_id, uuid.uuid4())

    assert len(result) == 2
    for item in result:
        assert not hasattr(item, "raw_key") or not item.raw_key  # raw_key absent from ApiKeyResponse


@pytest.mark.asyncio
async def test_revoke_soft_deletes_key():
    svc, repo, org_repo, membership_repo = make_service()
    org_id = uuid.uuid4()
    _with_admin_access(org_repo, membership_repo, org_id)
    key = make_key(org_id=org_id)
    repo.get_by_id_and_org.return_value = key

    await svc.revoke(org_id, uuid.uuid4(), key.id)
    repo.soft_delete.assert_called_once_with(key)


@pytest.mark.asyncio
async def test_revoke_raises_not_found_for_missing_key():
    svc, repo, org_repo, membership_repo = make_service()
    org_id = uuid.uuid4()
    _with_admin_access(org_repo, membership_repo, org_id)
    repo.get_by_id_and_org.return_value = None

    with pytest.raises(NotFoundError):
        await svc.revoke(org_id, uuid.uuid4(), uuid.uuid4())


@pytest.mark.asyncio
async def test_verify_finds_key_by_hash():
    svc, repo, _, _ = make_service()
    raw = "sk_somerawkey"
    expected_hash = hashlib.sha256(raw.encode()).hexdigest()
    stored_key = make_key(key_hash=expected_hash)
    repo.get_by_hash.return_value = stored_key

    result = await svc.verify(raw)

    repo.get_by_hash.assert_called_once_with(expected_hash)
    assert result == stored_key


@pytest.mark.asyncio
async def test_verify_returns_none_for_invalid_key():
    svc, repo, _, _ = make_service()
    repo.get_by_hash.return_value = None

    result = await svc.verify("sk_badkey")
    assert result is None
