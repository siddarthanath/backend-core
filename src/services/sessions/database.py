"""Database session — async SQLAlchemy engine and session factory from DatabaseSettings."""

# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Standard Library
from contextlib import asynccontextmanager
from typing import AsyncGenerator

# Third Party
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

# Internal
from src.configs.settings import database_settings
from src.utils.logging import get_logger

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #

log = get_logger(__name__)


class DatabaseSession:
    """Manages the async SQLAlchemy engine and session factory.

    Instantiated once at startup via lifespan, registered in db_registry,
    and resolved per-request via the get_db dependency.
    Swap databases by changing DATABASE_URL in settings — no code changes needed.

    """

    def __init__(self) -> None:
        self._engine: AsyncEngine | None = None
        self._session_factory: async_sessionmaker[AsyncSession] | None = None

    def initialise(self) -> None:
        """Create the async engine and session factory from current settings.

        Raises:
            RuntimeError: If called more than once without closing first.

        """
        if self._engine is not None:
            raise RuntimeError("DatabaseSession already initialised.")

        self._engine = create_async_engine(
            database_settings.DATABASE_URL,
            pool_size=database_settings.DATABASE_POOL_SIZE,
            max_overflow=database_settings.DATABASE_MAX_OVERFLOW,
            pool_timeout=database_settings.DATABASE_POOL_TIMEOUT,
            pool_recycle=database_settings.DATABASE_POOL_RECYCLE,
            echo=False,
        )
        self._session_factory = async_sessionmaker(
            bind=self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        log.info("db.engine_initialised")

    async def close(self) -> None:
        """Dispose the engine and release all pool connections."""
        if self._engine is not None:
            await self._engine.dispose()
            self._engine = None
            self._session_factory = None
            log.info("db.engine_disposed")

    def get_session(self) -> AsyncSession:
        """Return a new AsyncSession from the session factory.

        Returns:
            AsyncSession: A new session. Caller is responsible for closing it.

        Raises:
            RuntimeError: If initialise() has not been called.

        """
        if self._session_factory is None:
            raise RuntimeError("DatabaseSession not initialised. Call initialise() first.")
        return self._session_factory()


@asynccontextmanager
async def transaction(session: AsyncSession) -> AsyncGenerator[AsyncSession, None]:
    """Wrap a block of service code in a single commit/rollback unit.

    Usage:
        async with transaction(session) as s:
            await repo.create(s, data)
            await other_repo.update(s, ...)

    Commits on success, rolls back on any exception, always closes the session.
    Avoids duplicating try/except/rollback/finally in every service method.

    Args:
        session (AsyncSession): The session to wrap.

    Yields:
        AsyncSession: The same session, within a transaction.

    Raises:
        Exception: Re-raises any exception after rolling back.

    """
    try:
        yield session
        await session.commit()
    except Exception:
        try:
            await session.rollback()
        except Exception:
            pass  # original exception takes priority over rollback failure
        raise
    finally:
        await session.close()