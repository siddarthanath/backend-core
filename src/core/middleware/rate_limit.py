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


# DEPLOYMENT NOTE: storage is in-memory by default. That means each worker
# process keeps its OWN counters — run N uvicorn/gunicorn workers and the
# effective limit is roughly N× the configured value, and every restart resets
# all counts. Fine for a single-process dev server; for multi-process production
# point slowapi at a shared store by passing storage_uri, e.g.:
#     Limiter(key_func=get_rate_limit_key,
#             default_limits=[app_settings.RATE_LIMIT_DEFAULT],
#             storage_uri=app_settings.REDIS_URL)
# See docs/DEPLOYMENT.md.
limiter = Limiter(
    key_func=get_rate_limit_key,
    default_limits=[app_settings.RATE_LIMIT_DEFAULT],
)
