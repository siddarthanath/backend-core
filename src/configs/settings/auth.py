"""Auth settings — Supabase JWT verification (backend decodes only, never issues)."""

# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Third Party
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #


class AuthSettings(BaseSettings):
    """Supabase project credentials for JWT verification."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    SUPABASE_URL: str
    SUPABASE_JWT_SECRET: str = ""  # unused for ES256 — JWKS endpoint used instead
    SUPABASE_ANON_KEY: str
    SUPABASE_SERVICE_ROLE_KEY: str = ""

    @model_validator(mode="after")
    def _require_service_role_key(self) -> "AuthSettings":
        if not self.SUPABASE_SERVICE_ROLE_KEY:
            raise ValueError(
                "SUPABASE_SERVICE_ROLE_KEY is required. "
                "All Supabase admin calls (delete_user, update_email, update_password) will fail without it."
            )
        return self