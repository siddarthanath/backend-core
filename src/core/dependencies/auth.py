"""Auth dependency — decodes Supabase JWT and returns typed UserClaims."""

# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Third Party
import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

# Internal
from src.configs.settings import auth_settings
from src.core.context import set_request_user_id
from src.core.exceptions.types import AuthException
from src.schemas.auth import UserClaims

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #

# NOTE: Alternative — verify via Supabase Auth HTTP API (`supabase.auth.get_user(token)`).
# That approach makes an HTTP call to Supabase on every authenticated request, enabling real-time
# token revocation (useful for "logout from all devices" with instant effect). The tradeoff is
# ~50-200ms added latency per request and a hard dependency on Supabase API availability.
# Current approach (local PyJWT decode) is <1ms and fails only if the JWT secret is wrong.
# Switch if real-time revocation becomes a product requirement — layer it on top by maintaining
# a server-side blocklist of revoked `jti` claims checked after local decode.

_bearer = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
) -> UserClaims:
    """Decode and verify a Supabase JWT, returning the caller's claims.

    Args:
        credentials (HTTPAuthorizationCredentials): Bearer token from the Authorization header.

    Returns:
        UserClaims: Decoded sub, email, and role from the verified token.

    Raises:
        AuthException: If the token is missing, expired, or invalid.

    """
    # PROVIDER SWAP POINT (backend)
    # If/when you swap auth providers, you rewrite lib/supabase/client.ts (frontend) + this block —
    # the rest of the app (repositories, services, endpoints) doesn't change.
    # Supabase uses HS256 + shared JWT secret. Auth0/Firebase use RS256 + JWKS endpoint —
    # swap algorithm, key source, and audience claim accordingly. UserClaims shape stays the same.
    try:
        payload = jwt.decode(
            credentials.credentials,
            auth_settings.SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            audience="authenticated",
            issuer=f"{auth_settings.SUPABASE_URL}/auth/v1",
            leeway=10,
        )
    except jwt.ExpiredSignatureError:
        raise AuthException(message="Token expired")
    except jwt.InvalidTokenError:
        raise AuthException(message="Invalid token")

    claims = UserClaims(
        sub=payload["sub"],
        email=payload.get("email", ""),
        role=payload.get("role", "authenticated"),
    )
    set_request_user_id(claims.sub)
    return claims
