"""Shared test fixtures — app client, database session, and auth helpers."""

# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Standard Library
import uuid
from collections.abc import AsyncGenerator

# Third Party
import pytest
import pytest_asyncio
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

# Internal
from src.core.dependencies.auth import get_current_user
from src.main import app
from src.schemas.auth import UserClaims

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


@pytest_asyncio.fixture
async def db_session(client: AsyncClient) -> AsyncGenerator[AsyncSession, None]:
    """Yield a direct DB session for test setup and teardown.

    Depends on client to guarantee the lifespan has run and db_registry is populated.

    Yields:
        AsyncSession: Open session — caller is responsible for commit/rollback.

    """
    from src.core.registry import db_registry

    db = db_registry.get("default")
    session = db.get_session()
    try:
        yield session
    finally:
        await session.close()


@pytest.fixture
def user_id() -> uuid.UUID:
    """Fresh random UUID per test — guarantees isolation between test users."""
    return uuid.uuid4()


@pytest_asyncio.fixture
async def authed_client(
    client: AsyncClient,
    user_id: uuid.UUID,
) -> AsyncGenerator[AsyncClient, None]:
    """Client with get_current_user overridden for a test user.

    Overrides the auth dependency so tests do not need a real Supabase JWT.
    Cleans up the override after each test.

    Yields:
        AsyncClient: Authenticated test client.

    """
    claims = UserClaims(
        sub=str(user_id),
        email=f"test-{user_id}@example.com",
        role="authenticated",
    )
    app.dependency_overrides[get_current_user] = lambda: claims
    yield client
    app.dependency_overrides.pop(get_current_user, None)
