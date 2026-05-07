"""External service settings — Stripe, email. Empty stubs until Round 5."""

# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Third Party
from pydantic_settings import BaseSettings, SettingsConfigDict

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #


class ExternalSettings(BaseSettings):
    """Third-party service API keys. Wired up in Round 5 (billing)."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    STRIPE_SECRET_KEY: str = ""
    RESEND_API_KEY: str = ""