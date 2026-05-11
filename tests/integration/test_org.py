"""Integration tests for organisation and membership endpoints."""

# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Standard Library
import uuid

# Third Party
import pytest
from httpx import AsyncClient
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

# Internal
from src.core.dependencies.auth import get_current_user
from src.main import app
from src.models.org import Organisation
from src.models.user import UserProfile
from src.schemas.auth import UserClaims

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #


def _override_user(uid: uuid.UUID) -> None:
    """Switch the auth override to a different user mid-test."""
    claims = UserClaims(sub=str(uid), email=f"test-{uid}@example.com", role="authenticated")
    app.dependency_overrides[get_current_user] = lambda: claims


async def _seed_user(client: AsyncClient, uid: uuid.UUID) -> None:
    """Create a user profile by hitting GET /user/me as that user."""
    _override_user(uid)
    await client.get("/api/v1/user/me")


async def _cleanup(
    db_session: AsyncSession,
    org_ids: list[uuid.UUID],
    user_ids: list[uuid.UUID],
) -> None:
    """Delete test orgs (cascades memberships) then test users."""
    if org_ids:
        await db_session.execute(delete(Organisation).where(Organisation.id.in_(org_ids)))
    if user_ids:
        await db_session.execute(delete(UserProfile).where(UserProfile.id.in_(user_ids)))
    await db_session.commit()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_create_org_returns_201_and_creator_is_owner(
    authed_client: AsyncClient,
    user_id: uuid.UUID,
    db_session: AsyncSession,
) -> None:
    await authed_client.get("/api/v1/user/me")
    slug = f"test-org-{uuid.uuid4().hex[:8]}"

    response = await authed_client.post("/api/v1/orgs", json={"name": "My Org", "slug": slug})

    assert response.status_code == 201
    data = response.json()
    assert data["slug"] == slug
    assert data["name"] == "My Org"
    org_id = uuid.UUID(data["id"])

    members = await authed_client.get(f"/api/v1/orgs/{org_id}/members")
    roles = {m["user_id"]: m["role"] for m in members.json()}
    assert roles[str(user_id)] == "owner"

    await _cleanup(db_session, [org_id], [user_id])


@pytest.mark.integration
@pytest.mark.asyncio
async def test_create_org_duplicate_slug_returns_409(
    authed_client: AsyncClient,
    user_id: uuid.UUID,
    db_session: AsyncSession,
) -> None:
    await authed_client.get("/api/v1/user/me")
    slug = f"test-dup-{uuid.uuid4().hex[:8]}"

    r1 = await authed_client.post("/api/v1/orgs", json={"name": "First", "slug": slug})
    r2 = await authed_client.post("/api/v1/orgs", json={"name": "Second", "slug": slug})

    assert r1.status_code == 201
    assert r2.status_code == 409

    await _cleanup(db_session, [uuid.UUID(r1.json()["id"])], [user_id])


@pytest.mark.integration
@pytest.mark.asyncio
async def test_list_orgs_returns_all_user_orgs(
    authed_client: AsyncClient,
    user_id: uuid.UUID,
    db_session: AsyncSession,
) -> None:
    await authed_client.get("/api/v1/user/me")
    slug1 = f"org-a-{uuid.uuid4().hex[:8]}"
    slug2 = f"org-b-{uuid.uuid4().hex[:8]}"
    r1 = await authed_client.post("/api/v1/orgs", json={"name": "Org A", "slug": slug1})
    r2 = await authed_client.post("/api/v1/orgs", json={"name": "Org B", "slug": slug2})

    response = await authed_client.get("/api/v1/orgs")

    assert response.status_code == 200
    slugs = {o["slug"] for o in response.json()}
    assert slug1 in slugs
    assert slug2 in slugs

    await _cleanup(
        db_session,
        [uuid.UUID(r1.json()["id"]), uuid.UUID(r2.json()["id"])],
        [user_id],
    )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_org_non_member_returns_403(
    authed_client: AsyncClient,
    user_id: uuid.UUID,
    db_session: AsyncSession,
) -> None:
    await authed_client.get("/api/v1/user/me")
    slug = f"test-nm-{uuid.uuid4().hex[:8]}"
    r = await authed_client.post("/api/v1/orgs", json={"name": "Private Org", "slug": slug})
    org_id = uuid.UUID(r.json()["id"])

    outsider_id = uuid.uuid4()
    await _seed_user(authed_client, outsider_id)
    response = await authed_client.get(f"/api/v1/orgs/{org_id}")

    assert response.status_code == 403

    _override_user(user_id)
    await _cleanup(db_session, [org_id], [user_id, outsider_id])


@pytest.mark.integration
@pytest.mark.asyncio
async def test_update_org_member_cannot_update_returns_403(
    authed_client: AsyncClient,
    user_id: uuid.UUID,
    db_session: AsyncSession,
) -> None:
    await authed_client.get("/api/v1/user/me")
    slug = f"test-upd-{uuid.uuid4().hex[:8]}"
    r = await authed_client.post("/api/v1/orgs", json={"name": "Org", "slug": slug})
    org_id = uuid.UUID(r.json()["id"])

    member_id = uuid.uuid4()
    await _seed_user(authed_client, member_id)

    _override_user(user_id)
    invite_r = await authed_client.post(
        f"/api/v1/orgs/{org_id}/members",
        json={"email": f"test-{member_id}@example.com", "role": "member"},
    )
    assert invite_r.status_code == 201

    _override_user(member_id)
    await authed_client.post(f"/api/v1/orgs/{org_id}/members/accept")

    response = await authed_client.patch(f"/api/v1/orgs/{org_id}", json={"name": "Hacked"})
    assert response.status_code == 403

    _override_user(user_id)
    await _cleanup(db_session, [org_id], [user_id, member_id])


@pytest.mark.integration
@pytest.mark.asyncio
async def test_invite_and_accept_member(
    authed_client: AsyncClient,
    user_id: uuid.UUID,
    db_session: AsyncSession,
) -> None:
    await authed_client.get("/api/v1/user/me")
    slug = f"test-inv-{uuid.uuid4().hex[:8]}"
    r = await authed_client.post("/api/v1/orgs", json={"name": "Invite Org", "slug": slug})
    org_id = uuid.UUID(r.json()["id"])

    invitee_id = uuid.uuid4()
    await _seed_user(authed_client, invitee_id)

    _override_user(user_id)
    invite_r = await authed_client.post(
        f"/api/v1/orgs/{org_id}/members",
        json={"email": f"test-{invitee_id}@example.com", "role": "member"},
    )
    assert invite_r.status_code == 201
    assert invite_r.json()["status"] == "invited"

    _override_user(invitee_id)
    accept_r = await authed_client.post(f"/api/v1/orgs/{org_id}/members/accept")
    assert accept_r.status_code == 200
    assert accept_r.json()["status"] == "active"

    _override_user(user_id)
    members_r = await authed_client.get(f"/api/v1/orgs/{org_id}/members")
    member_user_ids = {m["user_id"] for m in members_r.json()}
    assert str(invitee_id) in member_user_ids

    await _cleanup(db_session, [org_id], [user_id, invitee_id])


@pytest.mark.integration
@pytest.mark.asyncio
async def test_change_role_owner_can_promote_member_to_admin(
    authed_client: AsyncClient,
    user_id: uuid.UUID,
    db_session: AsyncSession,
) -> None:
    await authed_client.get("/api/v1/user/me")
    slug = f"test-role-{uuid.uuid4().hex[:8]}"
    r = await authed_client.post("/api/v1/orgs", json={"name": "Role Org", "slug": slug})
    org_id = uuid.UUID(r.json()["id"])

    member_id = uuid.uuid4()
    await _seed_user(authed_client, member_id)

    _override_user(user_id)
    await authed_client.post(
        f"/api/v1/orgs/{org_id}/members",
        json={"email": f"test-{member_id}@example.com", "role": "member"},
    )
    _override_user(member_id)
    await authed_client.post(f"/api/v1/orgs/{org_id}/members/accept")

    _override_user(user_id)
    response = await authed_client.patch(
        f"/api/v1/orgs/{org_id}/members/{member_id}",
        json={"role": "admin"},
    )

    assert response.status_code == 200
    assert response.json()["role"] == "admin"

    await _cleanup(db_session, [org_id], [user_id, member_id])


@pytest.mark.integration
@pytest.mark.asyncio
async def test_change_role_member_cannot_promote_returns_403(
    authed_client: AsyncClient,
    user_id: uuid.UUID,
    db_session: AsyncSession,
) -> None:
    await authed_client.get("/api/v1/user/me")
    slug = f"test-norole-{uuid.uuid4().hex[:8]}"
    r = await authed_client.post("/api/v1/orgs", json={"name": "No Role Org", "slug": slug})
    org_id = uuid.UUID(r.json()["id"])

    member_id = uuid.uuid4()
    await _seed_user(authed_client, member_id)

    _override_user(user_id)
    await authed_client.post(
        f"/api/v1/orgs/{org_id}/members",
        json={"email": f"test-{member_id}@example.com", "role": "member"},
    )
    _override_user(member_id)
    await authed_client.post(f"/api/v1/orgs/{org_id}/members/accept")

    response = await authed_client.patch(
        f"/api/v1/orgs/{org_id}/members/{user_id}",
        json={"role": "admin"},
    )

    assert response.status_code == 403

    _override_user(user_id)
    await _cleanup(db_session, [org_id], [user_id, member_id])


@pytest.mark.integration
@pytest.mark.asyncio
async def test_remove_member(
    authed_client: AsyncClient,
    user_id: uuid.UUID,
    db_session: AsyncSession,
) -> None:
    await authed_client.get("/api/v1/user/me")
    slug = f"test-rm-{uuid.uuid4().hex[:8]}"
    r = await authed_client.post("/api/v1/orgs", json={"name": "Remove Org", "slug": slug})
    org_id = uuid.UUID(r.json()["id"])

    member_id = uuid.uuid4()
    await _seed_user(authed_client, member_id)

    _override_user(user_id)
    await authed_client.post(
        f"/api/v1/orgs/{org_id}/members",
        json={"email": f"test-{member_id}@example.com", "role": "member"},
    )
    _override_user(member_id)
    await authed_client.post(f"/api/v1/orgs/{org_id}/members/accept")

    _override_user(user_id)
    remove_r = await authed_client.delete(f"/api/v1/orgs/{org_id}/members/{member_id}")
    assert remove_r.status_code == 200

    members_r = await authed_client.get(f"/api/v1/orgs/{org_id}/members")
    member_user_ids = {m["user_id"] for m in members_r.json()}
    assert str(member_id) not in member_user_ids

    await _cleanup(db_session, [org_id], [user_id, member_id])
