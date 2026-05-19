"""App-level settings — name, version, CORS, timeouts."""

# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Third-Party Library
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #


class AppSettings(BaseSettings):
    """Core application settings loaded from environment."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    APP_NAME: str = "backend-core"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    CORS_ORIGINS: list[str] = Field(default=["http://localhost:3000"])
    FRONTEND_BASE_URL: str = "http://localhost:3000"
    REQUEST_TIMEOUT_SECONDS: int = 30
    RATE_LIMIT_DEFAULT: str = "60/minute"