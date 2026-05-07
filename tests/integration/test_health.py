"""Integration tests for health and readiness endpoints."""

# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Third Party
import pytest
from httpx import AsyncClient

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #


@pytest.mark.asyncio
async def test_health_returns_ok(client: AsyncClient) -> None:
    response = await client.get("/api/v1/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data
    assert "timestamp" in data


@pytest.mark.asyncio
async def test_ready_database_ok(client: AsyncClient) -> None:
    response = await client.get("/api/v1/ready")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert data["checks"]["database"] == "ok"


@pytest.mark.asyncio
async def test_health_response_headers(client: AsyncClient) -> None:
    response = await client.get("/api/v1/health")

    assert "x-request-id" in response.headers