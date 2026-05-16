"""User endpoints — profile management and account operations."""

# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Standard Library
import uuid

# Third Party
from fastapi import APIRouter, Request

# Internal
from src.core.dependencies import AuthSvc, CurrentUserClaims, CurrentUserID, OrgSvc, UserSvc
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

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #

router = APIRouter(prefix="/user", tags=["User"])


@router.get("/me", response_model=UserMeResponse)
@limiter.limit("120/minute")
async def get_me(
    request: Request,
    claims: CurrentUserClaims,
    service: UserSvc,
    org_service: OrgSvc,
) -> UserMeResponse:
    """Return the authenticated user's profile with billing and org context.

    Creates the profile and personal org on first login (B2C pattern — idempotent).

    B2B note: remove the org_service call and org_id field. Let clients call
    POST /orgs to create named team workspaces explicitly during onboarding.

    """
    user_id = uuid.UUID(claims.sub)
    user = await service.get_or_create(user_id, email=claims.email, full_name=claims.full_name)
    org = await org_service.get_or_create_personal(user_id, email=claims.email)
    return UserMeResponse(
        id=user.id,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        created_at=user.created_at,
        org_count=1,
        org_id=org.id,
    )


@router.patch("/me", response_model=UserProfileResponse)
@limiter.limit("30/minute")
async def update_profile(
    request: Request,
    body: UpdateProfileRequest,
    user_id: CurrentUserID,
    service: UserSvc,
) -> UserProfileResponse:
    """Update the authenticated user's display name."""
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
    auth_service: AuthSvc,
) -> MessageResponse:
    """Trigger a Supabase password reset email. Always returns success to prevent email enumeration."""
    await auth_service.send_password_reset(body.email)
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
    auth_service: AuthSvc,
) -> MessageResponse:
    """Initiate an email change via the Supabase admin API."""
    await auth_service.update_email(user_id, str(body.new_email))
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
    auth_service: AuthSvc,
) -> MessageResponse:
    """Update the authenticated user's password via the Supabase admin API."""
    await auth_service.update_password(user_id, body.new_password)
    return MessageResponse(message="Password updated successfully.")


@router.delete("/account", response_model=MessageResponse)
@limiter.limit("3/minute")
async def delete_account(
    request: Request,
    body: DeleteAccountRequest,
    user_id: CurrentUserID,
    service: UserSvc,
    org_service: OrgSvc,
    auth_service: AuthSvc,
) -> MessageResponse:
    """Hard-delete the user's profile and auth record.

    Order: clean up sole-owned orgs (OrgService) → delete profile (UserService) →
    delete Supabase auth user (AuthService). DB CASCADE handles memberships/subscriptions.

    body.confirmation must equal "DELETE MY ACCOUNT".

    """
    await org_service.cleanup_for_deleted_user(user_id)
    await service.delete(user_id)
    # Auth delete runs last. If this fails after profile is already hard-deleted,
    # the Supabase auth record lingers but the DB row is gone — user is locked out
    # on next login. No automatic recovery; requires manual Supabase admin cleanup.
    # Acceptable risk for a template; wrap in a retry/dead-letter queue for production.
    await auth_service.delete_user(user_id)
    return MessageResponse(
        message="Account deleted.",
        detail="All your data has been permanently removed.",
    )
