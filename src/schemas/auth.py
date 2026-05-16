"""Auth schemas — JWT claim shape extracted from Supabase tokens."""

# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Third Party
from pydantic import BaseModel

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #


class UserClaims(BaseModel):
    """Decoded claims from a verified Supabase JWT.

    Populated by the get_current_user dependency and injected into handlers
    that require authentication.

    """

    sub: str
    email: str
    role: str
    full_name: str | None = None