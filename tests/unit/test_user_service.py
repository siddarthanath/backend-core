"""Unit tests for UserService — mocks the repository layer."""

# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Standard Library
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

# Third Party
import pytest

# Internal
from src.core.exceptions.types import NotFoundError
from src.models.user import UserProfile
from src.services.user.service import UserService

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #


def _make_profile(**overrides: object) -> UserProfile:
    now = datetime.now(timezone.utc)
    defaults: dict[str, object] = {
        "id": uuid.uuid4(),
        "email": "test@example.com",
        "first_name": None,
        "last_name": None,
        "stripe_customer_id": None,
        "created_at": now,
        "updated_at": now,
        "deleted_at": None,
    }
    defaults.update(overrides)
    return UserProfile(**defaults)  # type: ignore[arg-type]


def _make_service() -> tuple[UserService, MagicMock]:
    """Return a UserService with a mocked session and repo."""
    session = MagicMock()
    service = UserService(session)
    service.repo = MagicMock()
    return service, service.repo


class TestGetMe:
    async def test_returns_profile_when_found(self) -> None:
        service, repo = _make_service()
        user_id = uuid.uuid4()
        profile = _make_profile(id=user_id)
        repo.get_by_id = AsyncMock(return_value=profile)

        result = await service.get_me(user_id)

        repo.get_by_id.assert_called_once_with(user_id)
        assert result is profile

    async def test_raises_not_found_when_missing(self) -> None:
        service, repo = _make_service()
        user_id = uuid.uuid4()
        repo.get_by_id = AsyncMock(return_value=None)

        with pytest.raises(NotFoundError) as exc_info:
            await service.get_me(user_id)

        assert exc_info.value.status_code == 404
        assert "User" in exc_info.value.message


class TestGetOrCreate:
    async def test_returns_existing_profile(self) -> None:
        service, repo = _make_service()
        user_id = uuid.uuid4()
        existing = _make_profile(id=user_id, email="existing@example.com")
        repo.upsert_from_supabase = AsyncMock(return_value=existing)

        result = await service.get_or_create(user_id, email="existing@example.com")

        assert result is existing
        repo.upsert_from_supabase.assert_called_once_with(
            user_id=user_id, email="existing@example.com"
        )


class TestUpdateProfile:
    async def test_updates_only_provided_fields(self) -> None:
        service, repo = _make_service()
        user_id = uuid.uuid4()
        profile = _make_profile(id=user_id, first_name="Old")
        updated = _make_profile(id=user_id, first_name="New")
        repo.get_by_id = AsyncMock(return_value=profile)
        repo.update = AsyncMock(return_value=updated)

        result = await service.update_profile(user_id, first_name="New")

        repo.update.assert_called_once_with(profile, first_name="New")
        assert result is updated

    async def test_skips_none_fields(self) -> None:
        service, repo = _make_service()
        user_id = uuid.uuid4()
        profile = _make_profile(id=user_id)
        repo.get_by_id = AsyncMock(return_value=profile)
        repo.update = AsyncMock(return_value=profile)

        await service.update_profile(user_id, first_name=None, last_name=None)

        repo.update.assert_called_once_with(profile)

    async def test_raises_not_found_for_unknown_user(self) -> None:
        service, repo = _make_service()
        repo.get_by_id = AsyncMock(return_value=None)

        with pytest.raises(NotFoundError):
            await service.update_profile(uuid.uuid4(), first_name="X")


class TestDelete:
    async def test_soft_deletes_existing_profile(self) -> None:
        service, repo = _make_service()
        user_id = uuid.uuid4()
        profile = _make_profile(id=user_id)
        repo.get_by_id = AsyncMock(return_value=profile)
        repo.soft_delete = AsyncMock(return_value=profile)

        await service.delete(user_id)

        repo.soft_delete.assert_called_once_with(profile)

    async def test_raises_not_found_for_unknown_user(self) -> None:
        service, repo = _make_service()
        repo.get_by_id = AsyncMock(return_value=None)

        with pytest.raises(NotFoundError):
            await service.delete(uuid.uuid4())
