"""Shared test fixtures — app client and database session."""

# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Standard Library
from collections.abc import AsyncGenerator

# Third Party
import pytest_asyncio
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient

# Internal
from src.main import app

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #


@pytest_asyncio.fixture(scope="session")
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Yield an httpx AsyncClient wired to the FastAPI app via ASGI transport.

    LifespanManager triggers the app's lifespan (startup/shutdown), so db_registry
    is populated before any test runs. Uses real DB — no mocks.

    Yields:
        AsyncClient: Test client for making HTTP requests.

    """
    async with LifespanManager(app) as manager:
        async with AsyncClient(transport=ASGITransport(app=manager.app), base_url="http://test") as c:
            yield c