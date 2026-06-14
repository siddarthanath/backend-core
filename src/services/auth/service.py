"""AuthService — thin wrapper around the Supabase Admin SDK for server-side auth operations.

All user-facing auth (signup, login, OAuth) is handled entirely by Supabase on the frontend.
This service handles server-initiated operations only: delete, email update, password update.
"""

# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Standard Library
import uuid

# Third-Party Library
import anyio
import anyio.to_thread

# Private Library
from src.core.exceptions.types import ExternalServiceError
from src.utils.auth import get_supabase_admin_client, get_supabase_anon_client
from src.utils.logging import get_logger

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #

log = get_logger(__name__)


class AuthService:
    """Wraps Supabase Admin SDK. Sync SDK calls are offloaded to a thread via anyio.

    NOTE: These methods cannot be covered by automated integration tests without a live
    Supabase project. Test them manually after changing Supabase SDK versions.
    """

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
        except (
            Exception
        ) as e:  # Supabase SDK can raise any exception type; catch-all is intentional
            log.error("supabase_delete_user_failed", user_id=str(user_id), error=str(e))
            raise ExternalServiceError("Supabase", str(e))

    async def verify_password(self, email: str, password: str) -> bool:
        """Verify a user's current password by attempting a Supabase sign-in.

        Supabase owns the password hash — we never store it. A successful sign-in
        proves the password is correct. Used to re-authenticate before sensitive
        operations (e.g. password change) so a stolen JWT alone cannot take over
        an account: the attacker would also need to know the current password.

        Args:
            email (str): The user's email (from verified JWT claims).
            password (str): The plaintext current password to verify.

        Returns:
            bool: True if the password is correct, False otherwise.

        """
        client = get_supabase_anon_client()
        try:
            await anyio.to_thread.run_sync(
                lambda: client.auth.sign_in_with_password(
                    {"email": email, "password": password}
                )
            )
            return True
        except Exception:
            # Any failure (wrong password, network) is treated as "not verified".
            # We never leak which — the caller surfaces a single generic message.
            return False

    # NOTE: password reset is handled entirely on the frontend via
    # supabase.auth.resetPasswordForEmail (Supabase sends the email and hosts the
    # flow). No server-side method is provided: admin.generate_link only mints a
    # link, it does not send mail, so a backend reset method would silently no-op
    # without a transactional email provider wired in.

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
                lambda: client.auth.admin.update_user_by_id(
                    str(user_id), {"email": new_email}
                )
            )
        except (
            Exception
        ) as e:  # Supabase SDK can raise any exception type; catch-all is intentional
            log.error(
                "supabase_update_email_failed", user_id=str(user_id), error=str(e)
            )
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
                lambda: client.auth.admin.update_user_by_id(
                    str(user_id), {"password": new_password}
                )
            )
        except (
            Exception
        ) as e:  # Supabase SDK can raise any exception type; catch-all is intentional
            log.error(
                "supabase_update_password_failed", user_id=str(user_id), error=str(e)
            )
            raise ExternalServiceError("Supabase", str(e))
