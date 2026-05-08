"""Settings package — exposes per-concern singleton instances loaded from environment."""

# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Internal
from .auth import AuthSettings
from .base import AppSettings
from .database import DatabaseSettings
from .external import ExternalSettings

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #

# NOTE: An alternative to module-level singletons is wrapping each in @lru_cache (from functools).
# @lru_cache defers instantiation until first call and caches the result, making it easy to override
# in tests via cache_clear() + monkeypatching. For this project, real-env integration tests make
# that unnecessary — plain singletons are simpler and sufficient.

app_settings = AppSettings()
database_settings = DatabaseSettings()
auth_settings = AuthSettings()
external_settings = ExternalSettings()