"""Database connection settings — async SQLAlchemy pool configuration."""

# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Third Party
from pydantic_settings import BaseSettings, SettingsConfigDict

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #


class DatabaseSettings(BaseSettings):
    """PostgreSQL connection settings. Change DATABASE_URL only to swap databases."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    DATABASE_URL: str
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20
    DATABASE_POOL_TIMEOUT: int = 30
    DATABASE_POOL_RECYCLE: int = 3600