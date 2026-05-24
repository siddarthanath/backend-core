"""Rate limiting — global slowapi limiter, default 60 req/min per IP."""

# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Third-Party Library
from slowapi import Limiter
from slowapi.util import get_remote_address

# Private Library
from src.configs.settings import app_settings

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #

# Module-level limiter — registered on app.state in add_middleware(), used via @limiter.limit() decorator.
# key_func=get_remote_address limits by IP. This stops accidental hammering and simple bots but can be
# bypassed by IP rotation. For authenticated routes in the product layer, replace get_remote_address with
# a function that extracts the user ID from the JWT — that ties the limit to the account, not the IP.
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[app_settings.RATE_LIMIT_DEFAULT],
)
