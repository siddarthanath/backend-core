"""Integration tests for user profile endpoints."""

# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Standard Library
import uuid

# Third Party
import pytest
from httpx import AsyncClient
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

# Internal
from src.models.user import UserProfile

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_me_creates_profile_on_first_call(
    authed_client: AsyncClient,
    user_id: uuid.UUID,
    db_session: AsyncSession,
) -> None:
    response = await authed_client.get("/api/v1/user/me")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(user_id)
    assert data["email"] == f"test-{user_id}@example.com"

    await db_session.execute(delete(UserProfile).where(UserProfile.id == user_id))
    await db_session.commit()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_me_is_idempotent(
    authed_client: AsyncClient,
    user_id: uuid.UUID,
    db_session: AsyncSession,
) -> None:
    r1 = await authed_client.get("/api/v1/user/me")
    r2 = await authed_client.get("/api/v1/user/me")

    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r1.json()["id"] == r2.json()["id"]

    await db_session.execute(delete(UserProfile).where(UserProfile.id == user_id))
    await db_session.commit()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_update_profile_sets_display_name(
    authed_client: AsyncClient,
    user_id: uuid.UUID,
    db_session: AsyncSession,
) -> None:
    await authed_client.get("/api/v1/user/me")

    response = await authed_client.patch(
        "/api/v1/user/me",
        json={"first_name": "Ada", "last_name": "Lovelace"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["first_name"] == "Ada"
    assert data["last_name"] == "Lovelace"

    await db_session.execute(delete(UserProfile).where(UserProfile.id == user_id))
    await db_session.commit()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_update_profile_partial_update_leaves_other_fields(
    authed_client: AsyncClient,
    user_id: uuid.UUID,
    db_session: AsyncSession,
) -> None:
    await authed_client.get("/api/v1/user/me")
    await authed_client.patch("/api/v1/user/me", json={"first_name": "Ada", "last_name": "Lovelace"})

    response = await authed_client.patch("/api/v1/user/me", json={"first_name": "Grace"})

    assert response.status_code == 200
    data = response.json()
    assert data["first_name"] == "Grace"
    assert data["last_name"] == "Lovelace"

    await db_session.execute(delete(UserProfile).where(UserProfile.id == user_id))
    await db_session.commit()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_unauthenticated_get_me_returns_403(client: AsyncClient) -> None:
    response = await client.get("/api/v1/user/me")

    assert response.status_code == 403
