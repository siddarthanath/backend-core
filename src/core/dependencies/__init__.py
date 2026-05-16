"""Dependencies package — FastAPI dependency functions and typed aliases."""

# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Standard Library
import uuid
from typing import Annotated, TypeAlias

# Third Party
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

# Internal
from src.core.dependencies.auth import get_current_user
from src.core.dependencies.database import get_db
from src.repositories.billing import SubscriptionRepository
from src.repositories.org import MembershipRepository, OrgRepository
from src.repositories.user import UserRepository
from src.schemas.auth import UserClaims
from src.services.auth.service import AuthService
from src.services.billing.service import BillingOrchestrator, StripeBillingService
from src.services.org.service import OrgService
from src.services.user.service import UserService

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


# Base aliases — defined first so factory functions can reference them as type hints.
CurrentUserID: TypeAlias = Annotated[uuid.UUID, Depends(get_current_user_id)]
CurrentUserClaims: TypeAlias = Annotated[UserClaims, Depends(get_current_user)]
DBSession: TypeAlias = Annotated[AsyncSession, Depends(get_db)]


def get_user_service(session: DBSession) -> UserService:
    """Construct UserService with its repository for the current request session.

    Args:
        session (AsyncSession): The request-scoped DB session from get_db.

    Returns:
        UserService: Ready-to-use service instance.

    """
    return UserService(repo=UserRepository(session))


def get_org_service(session: DBSession) -> OrgService:
    """Construct OrgService with its repositories for the current request session.

    Args:
        session (AsyncSession): The request-scoped DB session from get_db.

    Returns:
        OrgService: Ready-to-use service instance.

    """
    return OrgService(
        org_repo=OrgRepository(session),
        membership_repo=MembershipRepository(session),
        user_repo=UserRepository(session),
    )


def get_auth_service() -> AuthService:
    """Construct AuthService — no DB session required (wraps Supabase Admin SDK).

    Returns:
        AuthService: Ready-to-use service instance.

    """
    return AuthService()


def get_billing_service(session: DBSession) -> BillingOrchestrator:
    """Construct BillingOrchestrator with its repositories and Stripe service.

    Args:
        session (AsyncSession): The request-scoped DB session from get_db.

    Returns:
        BillingOrchestrator: Ready-to-use orchestrator instance.

    """
    return BillingOrchestrator(
        subscription_repo=SubscriptionRepository(session),
        org_repo=OrgRepository(session),
        membership_repo=MembershipRepository(session),
        billing_svc=StripeBillingService(),
    )


# Service aliases — defined after their factory functions.
AuthSvc: TypeAlias = Annotated[AuthService, Depends(get_auth_service)]
UserSvc: TypeAlias = Annotated[UserService, Depends(get_user_service)]
OrgSvc: TypeAlias = Annotated[OrgService, Depends(get_org_service)]
BillingSvc: TypeAlias = Annotated[BillingOrchestrator, Depends(get_billing_service)]

__all__ = [
    "get_db",
    "get_current_user",
    "get_current_user_id",
    "get_auth_service",
    "get_user_service",
    "get_org_service",
    "get_billing_service",
    "CurrentUserID",
    "CurrentUserClaims",
    "DBSession",
    "AuthSvc",
    "UserSvc",
    "OrgSvc",
    "BillingSvc",
]
