"""Auth settings — Supabase JWT verification (backend decodes only, never issues)."""

# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Third Party
from pydantic_settings import BaseSettings, SettingsConfigDict

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #


class AuthSettings(BaseSettings):
    """Supabase project credentials for JWT verification."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    SUPABASE_URL: str
    SUPABASE_JWT_SECRET: str
    SUPABASE_ANON_KEY: str