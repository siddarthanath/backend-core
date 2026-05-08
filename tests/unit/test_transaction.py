"""Unit tests for the transaction() context manager."""

# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Standard Library
from unittest.mock import AsyncMock, call

# Third Party
import pytest

# Internal
from src.services.sessions.database import transaction

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #


@pytest.mark.asyncio
async def test_transaction_commits_on_success() -> None:
    """transaction() commits then closes the session when the block succeeds."""
    session = AsyncMock()

    async with transaction(session) as s:
        assert s is session

    session.commit.assert_awaited_once()
    session.rollback.assert_not_awaited()
    session.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_transaction_rolls_back_on_exception() -> None:
    """transaction() rolls back, closes the session, and re-raises on exception."""
    session = AsyncMock()

    with pytest.raises(ValueError, match="intentional"):
        async with transaction(session) as s:
            assert s is session
            raise ValueError("intentional")

    session.rollback.assert_awaited_once()
    session.commit.assert_not_awaited()
    session.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_transaction_closes_session_after_rollback() -> None:
    """transaction() always closes the session — even when rollback itself raises."""
    session = AsyncMock()
    session.rollback.side_effect = RuntimeError("rollback failed")

    with pytest.raises(ValueError, match="original"):
        async with transaction(session) as _:
            raise ValueError("original")

    # close() still called despite rollback failure
    session.close.assert_awaited_once()
