"""Integration tests for user endpoints — requires a live database."""

# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Standard Library
import uuid
from unittest.mock import patch

# Third Party
import pytest
from httpx import AsyncClient

# Internal
from src.schemas.auth import UserClaims

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #

_TEST_USER_ID = uuid.uuid4()
_TEST_CLAIMS = UserClaims(
    sub=str(_TEST_USER_ID),
    email="integtest@example.com",
    role="authenticated",
)


def _auth_override() -> UserClaims:
    return _TEST_CLAIMS


@pytest.mark.integration
class TestGetMe:
    async def test_creates_profile_on_first_request(self, client: AsyncClient) -> None:
        from src.core.dependencies.auth import get_current_user
        from src.main import app

        app.dependency_overrides[get_current_user] = _auth_override
        try:
            response = await client.get("/api/v1/user/me")
            assert response.status_code == 200
            data = response.json()
            assert data["email"] == "integtest@example.com"
            assert data["plan"] == "free"
            assert data["org_count"] == 0
        finally:
            app.dependency_overrides.clear()

    async def test_returns_401_without_token(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/user/me")
        assert response.status_code == 401


@pytest.mark.integration
class TestUpdateProfile:
    async def test_updates_name_fields(self, client: AsyncClient) -> None:
        from src.core.dependencies.auth import get_current_user
        from src.main import app

        app.dependency_overrides[get_current_user] = _auth_override
        try:
            # Ensure profile exists
            await client.get("/api/v1/user/me")

            response = await client.patch(
                "/api/v1/user/me",
                json={"first_name": "Alice", "last_name": "Smith"},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["first_name"] == "Alice"
            assert data["last_name"] == "Smith"
        finally:
            app.dependency_overrides.clear()

    async def test_partial_update_preserves_existing_fields(self, client: AsyncClient) -> None:
        from src.core.dependencies.auth import get_current_user
        from src.main import app

        app.dependency_overrides[get_current_user] = _auth_override
        try:
            # Set both fields
            await client.patch(
                "/api/v1/user/me",
                json={"first_name": "Alice", "last_name": "Smith"},
            )
            # Update only first_name
            response = await client.patch("/api/v1/user/me", json={"first_name": "Bob"})
            assert response.status_code == 200
            data = response.json()
            assert data["first_name"] == "Bob"
            assert data["last_name"] == "Smith"
        finally:
            app.dependency_overrides.clear()


@pytest.mark.integration
class TestPasswordReset:
    async def test_always_returns_200_regardless_of_email(self, client: AsyncClient) -> None:
        with patch("src.services.auth.service.get_supabase_admin_client") as mock_client:
            mock_client.return_value.auth.admin.generate_link.return_value = {}
            response = await client.post(
                "/api/v1/user/reset-password",
                json={"email": "nobody@example.com"},
            )
        assert response.status_code == 200
        data = response.json()
        assert "reset link" in data["message"]
