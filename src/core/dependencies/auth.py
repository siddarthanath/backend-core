"""Auth dependency — decodes Supabase JWT and returns typed UserClaims."""

# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Third Party
import jwt
from jwt import PyJWKClient
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from structlog.contextvars import bind_contextvars

# Internal
from src.configs.settings import auth_settings
from src.core.context import set_request_user_id
from src.core.exceptions.types import AuthException
from src.schemas.auth import UserClaims

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #

# NOTE: Newer Supabase projects sign JWTs with ES256 (asymmetric). Older projects used HS256
# with a shared secret. PyJWKClient fetches the public keys from Supabase's JWKS endpoint once
# and caches them — so local verification stays <1ms after the first request.
# PROVIDER SWAP POINT: swap SUPABASE_URL + JWKS path for Auth0/Firebase JWKS URIs.

_bearer = HTTPBearer()
_jwks_client = PyJWKClient(
    f"{auth_settings.SUPABASE_URL}/auth/v1/.well-known/jwks.json",
    cache_keys=True,
)


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
    try:
        signing_key = _jwks_client.get_signing_key_from_jwt(credentials.credentials)
        payload = jwt.decode(
            credentials.credentials,
            signing_key.key,
            algorithms=["ES256", "RS256", "HS256"],
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
        full_name=payload.get("user_metadata", {}).get("full_name"),
    )
    set_request_user_id(claims.sub)
    # Bind to user to flow into all downstream logs
    bind_contextvars(user_id=claims.sub)
    return claims
