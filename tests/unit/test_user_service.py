"""Unit tests for UserService — no database, all repositories mocked."""

# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Standard Library
import uuid
from unittest.mock import AsyncMock, MagicMock

# Third Party
import pytest

# Internal
from src.core.exceptions.types import NotFoundError
from src.repositories.user import UserRepository
from src.services.user.service import UserService

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #


def make_service() -> tuple[UserService, AsyncMock]:
    """Return a UserService wired to a mocked repository."""
    repo = AsyncMock(spec=UserRepository)
    return UserService(repo=repo), repo


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
    service, repo = make_service()
    repo.get_by_id.return_value = None

    with pytest.raises(NotFoundError):
        await service.get_me(uuid.uuid4())


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_me_returns_profile_when_found() -> None:
    service, repo = make_service()
    profile = make_profile()
    user_id = uuid.uuid4()
    repo.get_by_id.return_value = profile

    result = await service.get_me(user_id)

    repo.get_by_id.assert_awaited_once_with(user_id)
    assert result is profile


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_profile_passes_only_non_none_fields() -> None:
    service, repo = make_service()
    profile = make_profile()
    repo.get_by_id.return_value = profile
    repo.update.return_value = profile

    await service.update_profile(uuid.uuid4(), first_name="Ada", last_name=None)

    _, kwargs = repo.update.call_args
    assert "first_name" in kwargs
    assert "last_name" not in kwargs


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_profile_passes_both_fields_when_provided() -> None:
    service, repo = make_service()
    profile = make_profile()
    repo.get_by_id.return_value = profile
    repo.update.return_value = profile

    await service.update_profile(uuid.uuid4(), first_name="Ada", last_name="Lovelace")

    _, kwargs = repo.update.call_args
    assert kwargs["first_name"] == "Ada"
    assert kwargs["last_name"] == "Lovelace"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_delete_raises_not_found_when_no_profile() -> None:
    service, repo = make_service()
    repo.get_by_id.return_value = None

    with pytest.raises(NotFoundError):
        await service.delete(uuid.uuid4())


@pytest.mark.unit
@pytest.mark.asyncio
async def test_delete_calls_soft_delete_on_profile() -> None:
    service, repo = make_service()
    profile = make_profile()
    repo.get_by_id.return_value = profile

    await service.delete(uuid.uuid4())

    repo.soft_delete.assert_awaited_once_with(profile)
