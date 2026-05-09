"""Dependencies package — FastAPI dependency functions and typed aliases."""

# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Standard Library
import uuid
from typing import Annotated

# Third Party
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

# Internal
from src.core.dependencies.auth import get_current_user
from src.core.dependencies.database import get_db
from src.schemas.auth import UserClaims

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #


async def get_current_user_id(
    claims: Annotated[UserClaims, Depends(get_current_user)],
) -> uuid.UUID:
    """Extract the UUID from verified JWT claims.

    Args:
        claims (UserClaims): Decoded and verified token claims.

    Returns:
        uuid.UUID: The authenticated user's UUID.

    """
    return uuid.UUID(claims.sub)


CurrentUserID = Annotated[uuid.UUID, Depends(get_current_user_id)]
CurrentUserClaims = Annotated[UserClaims, Depends(get_current_user)]
DBSession = Annotated[AsyncSession, Depends(get_db)]

__all__ = [
    "get_db",
    "get_current_user",
    "get_current_user_id",
    "CurrentUserID",
    "CurrentUserClaims",
    "DBSession",
]
