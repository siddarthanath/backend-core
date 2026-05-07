"""Dependencies package — FastAPI dependency functions for DB sessions and auth."""

# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Internal
from src.core.dependencies.auth import get_current_user
from src.core.dependencies.database import get_db

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #

__all__ = ["get_db", "get_current_user"]
