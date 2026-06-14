"""Unit tests for AuthService — Supabase client mocked."""

# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Standard Library
from unittest.mock import MagicMock, patch

# Third-Party Library
import pytest

# Private Library
from src.services.auth.service import AuthService

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #


class TestVerifyPassword:
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_returns_true_on_successful_signin(self) -> None:
        client = MagicMock()
        with patch(
            "src.services.auth.service.get_supabase_anon_client", return_value=client
        ):
            result = await AuthService().verify_password("user@example.com", "correct")

        assert result is True
        client.auth.sign_in_with_password.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_returns_false_when_signin_raises(self) -> None:
        client = MagicMock()
        client.auth.sign_in_with_password.side_effect = Exception("invalid credentials")
        with patch(
            "src.services.auth.service.get_supabase_anon_client", return_value=client
        ):
            result = await AuthService().verify_password("user@example.com", "wrong")

        assert result is False
