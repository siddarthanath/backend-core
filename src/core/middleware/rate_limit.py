"""Rate limiting — global slowapi limiter, default 60 req/min per IP."""

# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Third Party
from slowapi import Limiter
from slowapi.util import get_remote_address

# Internal
from src.configs.settings import app_settings

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #

# Module-level limiter — registered on app.state in add_middleware(), used via @limiter.limit() decorator.
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[app_settings.RATE_LIMIT_DEFAULT],
)