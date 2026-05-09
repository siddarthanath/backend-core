"""Auth utilities — Supabase admin client factory."""

# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Third Party
from supabase import Client, create_client

# Internal
from src.configs.settings import auth_settings

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #


def get_supabase_admin_client() -> Client:
    """Return a Supabase client authenticated with the service role key.

    Uses the service role key, not the anon key — only call from server-side code.
    Never expose this client or its token to the frontend.

    Returns:
        Client: Supabase client with admin privileges.

    """
    return create_client(
        auth_settings.SUPABASE_URL,
        auth_settings.SUPABASE_SERVICE_ROLE_KEY,
    )
