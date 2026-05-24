"""Unit tests for the transaction() context manager."""

# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Standard Library
from unittest.mock import AsyncMock

# Third-Party Library
import pytest

# Private Library
from src.services.sessions.database import transaction

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #


class TestTransaction:
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_commits_on_success(self) -> None:
        """transaction() commits then closes the session when the block succeeds."""
        session = AsyncMock()

        async with transaction(session) as s:
            assert s is session

        session.commit.assert_awaited_once()
        session.rollback.assert_not_awaited()
        session.close.assert_awaited_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_rolls_back_on_exception(self) -> None:
        """transaction() rolls back, closes the session, and re-raises on exception."""
        session = AsyncMock()

        with pytest.raises(ValueError, match="intentional"):
            async with transaction(session) as s:
                assert s is session
                raise ValueError("intentional")

        session.rollback.assert_awaited_once()
        session.commit.assert_not_awaited()
        session.close.assert_awaited_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_closes_session_after_rollback(self) -> None:
        """transaction() always closes the session — even when rollback itself raises."""
        session = AsyncMock()
        session.rollback.side_effect = RuntimeError("rollback failed")

        with pytest.raises(ValueError, match="original"):
            async with transaction(session) as _:
                raise ValueError("original")

        # close() still called despite rollback failure
        session.close.assert_awaited_once()
