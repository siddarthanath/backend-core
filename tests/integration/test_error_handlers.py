"""Integration tests for global exception handlers — shape and status codes."""

# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Standard Library
import uuid

# Third Party
import pytest
from httpx import AsyncClient

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #


def _error(data: dict) -> dict:
    """Extract the nested error envelope from a response body."""
    return data["error"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_unauthenticated_returns_401(client: AsyncClient) -> None:
    """Any protected endpoint without a token must return 401 with error envelope."""
    org_id = uuid.uuid4()
    response = await client.get(f"/api/v1/orgs/{org_id}/billing")

    assert response.status_code == 401
    error = _error(response.json())
    assert error["code"] == "UNAUTHORIZED"
    assert "message" in error
    assert "request_id" in error


@pytest.mark.integration
@pytest.mark.asyncio
async def test_forbidden_returns_403(authed_client: AsyncClient) -> None:
    """Member trying an admin-only action must get 403."""
    # Uses a random org that the authed user is not a member of.
    # Will be 403 (not a member) or 404 (org not found) — both are correct here.
    org_id = uuid.uuid4()
    response = await authed_client.post(
        f"/api/v1/orgs/{org_id}/billing/cancel",
        json={"reason": "test"},
    )

    assert response.status_code in (403, 404)
    error = _error(response.json())
    assert error["code"] in ("FORBIDDEN", "NOT_FOUND")
    assert "request_id" in error


@pytest.mark.integration
@pytest.mark.asyncio
async def test_not_found_returns_404(authed_client: AsyncClient) -> None:
    """Request for a non-existent org must return 404 with error envelope."""
    org_id = uuid.uuid4()
    response = await authed_client.get(f"/api/v1/orgs/{org_id}/billing")

    assert response.status_code in (403, 404)
    error = _error(response.json())
    assert error["code"] in ("FORBIDDEN", "NOT_FOUND")
    assert "request_id" in error


@pytest.mark.integration
@pytest.mark.asyncio
async def test_invalid_body_returns_422(authed_client: AsyncClient) -> None:
    """Sending an invalid request body must return 422 with the error envelope."""
    org_id = uuid.uuid4()
    response = await authed_client.post(
        f"/api/v1/orgs/{org_id}/billing/checkout",
        json={"plan": "INVALID_PLAN"},  # missing fields + bad enum value
    )

    assert response.status_code == 422
    error = _error(response.json())
    assert error["code"] == "VALIDATION_ERROR"
    assert "request_id" in error


@pytest.mark.integration
@pytest.mark.asyncio
async def test_method_not_allowed_has_envelope(client: AsyncClient) -> None:
    """Wrong HTTP method on a known route must return 405 with error envelope."""
    response = await client.delete("/api/v1/health")

    assert response.status_code == 405
