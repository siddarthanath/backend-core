"""User endpoints — profile management and account operations."""

# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Standard Library
import uuid

# Third-Party Library
from fastapi import APIRouter, Request

# Private Library
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
from src.schemas.user.responses import UserMeResponse

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


@router.patch("/me", response_model=UserMeResponse)
@limiter.limit("30/minute")
async def update_profile(
    request: Request,
    body: UpdateProfileRequest,
    claims: CurrentUserClaims,
    service: UserSvc,
    org_service: OrgSvc,
) -> UserMeResponse:
    """Update the authenticated user's display name."""
    user_id = uuid.UUID(claims.sub)
    user = await service.update_profile(
        user_id,
        first_name=body.first_name,
        last_name=body.last_name,
    )
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
    """Soft-delete the user's profile and revoke their Supabase auth record.

    Order: delete Supabase auth (AuthService) → clean up sole-owned orgs (OrgService)
    → soft-delete profile (UserService).

    Auth is deleted first so that failure at any later step leaves no broken state:
    - If auth delete fails: nothing changed, user still has full access.
    - If org cleanup or profile soft-delete fails after auth delete: user cannot log in
      (auth record is gone), and the orphaned profile row is cleaned up by a periodic
      maintenance job (find profiles where deleted_at IS NULL but no Supabase auth user
      exists and soft-delete them). No manual intervention needed.

    body.confirmation must equal "DELETE MY ACCOUNT".

    Production pattern: replace this with status=pending_deletion and enqueue a
    background job to hard-delete the row, cancel Stripe, purge storage, and remove
    from email lists asynchronously with retries after a grace period.

    """
    await auth_service.delete_user(user_id)
    await org_service.cleanup_for_deleted_user(user_id)
    await service.delete(user_id)
    return MessageResponse(
        message="Account deleted.",
        detail="All your data has been permanently removed.",
    )
