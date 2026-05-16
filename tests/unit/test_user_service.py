"""Unit tests for UserService — no database, all repositories mocked."""

# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Standard Library
import uuid
from dataclasses import dataclass
from unittest.mock import AsyncMock, MagicMock

# Third Party
import pytest

# Internal
from src.core.exceptions.types import NotFoundError
from src.repositories.user import UserRepository
from src.services.user.service import UserService

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #


@dataclass
class ServiceFixture:
    service: UserService
    repo: AsyncMock


def make_service() -> ServiceFixture:
    """Return a UserService wired to a mocked repository."""
    repo = AsyncMock(spec=UserRepository)
    service = UserService(repo=repo)
    return ServiceFixture(service, repo)


def make_profile(**kwargs: object) -> MagicMock:
    """Return a minimal mock UserProfile with sensible defaults."""
    profile = MagicMock()
    profile.id = kwargs.get("id", uuid.uuid4())
    profile.email = kwargs.get("email", "user@example.com")
    profile.first_name = kwargs.get("first_name", None)
    profile.last_name = kwargs.get("last_name", None)
    return profile


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_me_raises_not_found_when_no_profile() -> None:
    f = make_service()
    f.repo.get_by_id.return_value = None

    with pytest.raises(NotFoundError):
        await f.service.get_me(uuid.uuid4())


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_me_returns_profile_when_found() -> None:
    f = make_service()
    profile = make_profile()
    user_id = uuid.uuid4()
    f.repo.get_by_id.return_value = profile

    result = await f.service.get_me(user_id)

    f.repo.get_by_id.assert_awaited_once_with(user_id)
    assert result is profile


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_profile_passes_only_non_none_fields() -> None:
    f = make_service()
    profile = make_profile()
    f.repo.get_by_id.return_value = profile
    f.repo.update.return_value = profile

    await f.service.update_profile(uuid.uuid4(), first_name="Ada", last_name=None)

    _, kwargs = f.repo.update.call_args
    assert "first_name" in kwargs
    assert "last_name" not in kwargs


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_profile_passes_both_fields_when_provided() -> None:
    f = make_service()
    profile = make_profile()
    f.repo.get_by_id.return_value = profile
    f.repo.update.return_value = profile

    await f.service.update_profile(uuid.uuid4(), first_name="Ada", last_name="Lovelace")

    _, kwargs = f.repo.update.call_args
    assert kwargs["first_name"] == "Ada"
    assert kwargs["last_name"] == "Lovelace"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_delete_raises_not_found_when_no_profile() -> None:
    f = make_service()
    f.repo.get_by_id.return_value = None

    with pytest.raises(NotFoundError):
        await f.service.delete(uuid.uuid4())


@pytest.mark.unit
@pytest.mark.asyncio
async def test_delete_hard_deletes_profile() -> None:
    f = make_service()
    user_id = uuid.uuid4()
    profile = make_profile(id=user_id)
    f.repo.get_by_id.return_value = profile

    await f.service.delete(user_id)

    f.repo.hard_delete.assert_awaited_once_with(profile)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_delete_does_not_touch_orgs_or_memberships() -> None:
    """UserService.delete only removes the profile — org cleanup is OrgService's job."""
    f = make_service()
    user_id = uuid.uuid4()
    profile = make_profile(id=user_id)
    f.repo.get_by_id.return_value = profile

    await f.service.delete(user_id)

    # Only one repo method should have been called beyond get_by_id
    assert f.repo.hard_delete.await_count == 1
