"""Rate limiting — global slowapi limiter, default 60 req/min per user/IP."""

# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Third-Party Library
import jwt as pyjwt
from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

# Private Library
from src.configs.settings import app_settings

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #


def get_rate_limit_key(request: Request) -> str:
    """Key authenticated requests by user ID, unauthenticated requests by IP.

    Decoding without signature verification is intentional — we are bucketing
    traffic, not authorising it. Real auth and verification happens in
    get_current_user. If the token is forged, get_current_user rejects it;
    the rate limit bucket is irrelevant at that point.
    """
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        token = auth.removeprefix("Bearer ")
        try:
            payload = pyjwt.decode(
                token,
                options={"verify_signature": False},
                algorithms=["ES256", "RS256"],
            )
            sub = payload.get("sub")
            if sub:
                return f"user:{sub}"
        except Exception:
            pass
    return get_remote_address(request)


limiter = Limiter(
    key_func=get_rate_limit_key,
    default_limits=[app_settings.RATE_LIMIT_DEFAULT],
)
