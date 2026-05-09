"""User endpoints — profile management and account operations."""

# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Standard Library
import uuid

# Third Party
from fastapi import APIRouter, Request

# Internal
from src.constants import Plan
from src.core.dependencies import CurrentUserClaims, CurrentUserID, DBSession
from src.core.middleware.rate_limit import limiter
from src.schemas.common import MessageResponse
from src.schemas.user.requests import (
    DeleteAccountRequest,
    RequestPasswordResetRequest,
    UpdateEmailRequest,
    UpdatePasswordRequest,
    UpdateProfileRequest,
)
from src.schemas.user.responses import UserMeResponse, UserProfileResponse
from src.services.auth.service import AuthService
from src.services.user.service import UserService

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #

router = APIRouter(prefix="/user", tags=["User"])


@router.get("/me", response_model=UserMeResponse)
@limiter.limit("120/minute")
async def get_me(
    request: Request,
    claims: CurrentUserClaims,
    session: DBSession,
) -> UserMeResponse:
    """Return the authenticated user's profile with billing and org context.

    Creates the profile on first login using email from the verified JWT.

    """
    user_id = uuid.UUID(claims.sub)
    service = UserService(session)
    user = await service.get_or_create(user_id, email=claims.email)
    return UserMeResponse(
        id=user.id,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        created_at=user.created_at,
        plan=Plan.FREE,
        org_count=0,
    )


@router.patch("/me", response_model=UserProfileResponse)
@limiter.limit("30/minute")
async def update_profile(
    request: Request,
    body: UpdateProfileRequest,
    user_id: CurrentUserID,
    session: DBSession,
) -> UserProfileResponse:
    """Update the authenticated user's display name."""
    service = UserService(session)
    user = await service.update_profile(
        user_id,
        first_name=body.first_name,
        last_name=body.last_name,
    )
    return UserProfileResponse.model_validate(user)


@router.post("/reset-password", response_model=MessageResponse)
@limiter.limit("5/minute")
async def request_password_reset(
    request: Request,
    body: RequestPasswordResetRequest,
) -> MessageResponse:
    """Trigger a Supabase password reset email. Always returns success to prevent email enumeration."""
    auth = AuthService()
    await auth.send_password_reset(body.email)
    return MessageResponse(
        message="If that email exists, we've sent a reset link.",
        detail="Check your inbox.",
    )


@router.put("/email", response_model=MessageResponse)
@limiter.limit("10/minute")
async def update_email(
    request: Request,
    body: UpdateEmailRequest,
    user_id: CurrentUserID,
) -> MessageResponse:
    """Initiate an email change via the Supabase admin API."""
    auth = AuthService()
    await auth.update_email(user_id, str(body.new_email))
    return MessageResponse(
        message="Email update initiated.",
        detail="Check your new address for a confirmation link.",
    )


@router.put("/password", response_model=MessageResponse)
@limiter.limit("10/minute")
async def update_password(
    request: Request,
    body: UpdatePasswordRequest,
    user_id: CurrentUserID,
) -> MessageResponse:
    """Update the authenticated user's password via the Supabase admin API."""
    auth = AuthService()
    await auth.update_password(user_id, body.new_password)
    return MessageResponse(message="Password updated successfully.")


@router.delete("/account", response_model=MessageResponse)
@limiter.limit("3/minute")
async def delete_account(
    request: Request,
    body: DeleteAccountRequest,
    user_id: CurrentUserID,
    session: DBSession,
) -> MessageResponse:
    """Soft-delete UserProfile then hard-delete the Supabase auth user.

    body.confirmation must equal "DELETE MY ACCOUNT".

    """
    user_service = UserService(session)
    auth_service = AuthService()
    await user_service.delete(user_id)
    await auth_service.delete_user(user_id)
    return MessageResponse(
        message="Account deleted.",
        detail="All your data has been permanently removed.",
    )
