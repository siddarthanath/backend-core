"""AuthService — thin wrapper around the Supabase Admin SDK for server-side auth operations.

All user-facing auth (signup, login, OAuth) is handled entirely by Supabase on the frontend.
This service handles server-initiated operations only: delete, email update, password update.
"""

# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Standard Library
import uuid

# Third Party
import anyio
import anyio.to_thread

# Internal
from src.core.exceptions.types import ExternalServiceError
from src.utils.auth import get_supabase_admin_client
from src.utils.logging import get_logger

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #

log = get_logger(__name__)


class AuthService:
    """Wraps Supabase Admin SDK. Sync SDK calls are offloaded to a thread via anyio."""

    async def delete_user(self, user_id: uuid.UUID) -> None:
        """Hard-delete the user from Supabase auth. Call after soft-deleting UserProfile.

        Args:
            user_id (uuid.UUID): The Supabase auth UUID to delete.

        Raises:
            ExternalServiceError: If the Supabase admin call fails.

        """
        try:
            client = get_supabase_admin_client()
            await anyio.to_thread.run_sync(
                lambda: client.auth.admin.delete_user(str(user_id))
            )
        except Exception as e:
            log.error("supabase_delete_user_failed", user_id=str(user_id), error=str(e))
            raise ExternalServiceError("Supabase", str(e))

    async def send_password_reset(self, email: str) -> None:
        """Trigger Supabase to send a password reset email.

        Args:
            email (str): The recipient email address.

        Raises:
            ExternalServiceError: If the Supabase admin call fails.

        """
        try:
            client = get_supabase_admin_client()
            await anyio.to_thread.run_sync(
                lambda: client.auth.admin.generate_link({"type": "recovery", "email": email})
            )
        except Exception as e:
            log.error("supabase_password_reset_failed", error=str(e))
            raise ExternalServiceError("Supabase", str(e))

    async def update_email(self, user_id: uuid.UUID, new_email: str) -> None:
        """Update the user's email via the Supabase admin API.

        Args:
            user_id (uuid.UUID): The Supabase auth UUID.
            new_email (str): The new email address.

        Raises:
            ExternalServiceError: If the Supabase admin call fails.

        """
        try:
            client = get_supabase_admin_client()
            await anyio.to_thread.run_sync(
                lambda: client.auth.admin.update_user_by_id(str(user_id), {"email": new_email})
            )
        except Exception as e:
            log.error("supabase_update_email_failed", user_id=str(user_id), error=str(e))
            raise ExternalServiceError("Supabase", str(e))

    async def update_password(self, user_id: uuid.UUID, new_password: str) -> None:
        """Update the user's password via the Supabase admin API.

        Args:
            user_id (uuid.UUID): The Supabase auth UUID.
            new_password (str): The new plaintext password (Supabase hashes it).

        Raises:
            ExternalServiceError: If the Supabase admin call fails.

        """
        try:
            client = get_supabase_admin_client()
            await anyio.to_thread.run_sync(
                lambda: client.auth.admin.update_user_by_id(str(user_id), {"password": new_password})
            )
        except Exception as e:
            log.error("supabase_update_password_failed", user_id=str(user_id), error=str(e))
            raise ExternalServiceError("Supabase", str(e))
