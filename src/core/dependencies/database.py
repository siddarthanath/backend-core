"""Database dependency — yields an AsyncSession from the registry session factory."""

# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Standard Library
from collections.abc import AsyncGenerator

# Third Party
from sqlalchemy.ext.asyncio import AsyncSession

# Internal
from src.core.registry import db_registry

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield an AsyncSession, closing it when the request completes.

    Yields:
        AsyncSession: A session bound to the registered database engine.

    """
    session = db_registry.get("default").get_session()
    async with session:
        yield session