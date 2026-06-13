"""User endpoints — profile management and account operations."""

# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Standard Library
import uuid

# Third-Party Library
from fastapi import APIRouter, Request

# Private Library
from src.core.dependencies import (
    AuthSvc,
    CurrentUserClaims,
    CurrentUserID,
    OrgSvc,
    UserSvc,
)
from src.core.exceptions.types import AppValidationError
from src.core.middleware.rate_limit import limiter
from src.schemas.common import MessageResponse
from src.schemas.user.requests import (
    DeleteAccountRequest,
    UpdatePasswordRequest,
    UpdateProfileRequest,
)
from src.schemas.user.responses import UserMeResponse, build_user_me_response

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
    user = await service.get_or_create(
        user_id,
        email=claims.email,
        first_name=claims.first_name,
        last_name=claims.last_name,
    )
    await org_service.get_or_create_personal(user_id, email=claims.email)
    orgs = await org_service.list_my_orgs(user_id)
    return build_user_me_response(user, orgs)


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
    orgs = await org_service.list_my_orgs(user_id)
    return build_user_me_response(user, orgs)


# PASSWORD RESET is handled entirely on the frontend via
# supabase.auth.resetPasswordForEmail — Supabase sends the email and hosts the
# reset flow. There is intentionally no backend endpoint for it: a server-side
# admin.generate_link() only mints a link, it does not send mail, so a backend
# endpoint would silently no-op without a transactional email provider wired in.


# EMAIL CHANGE — intentionally disabled in this template (see SecuritySection.tsx).
# Email is treated as fixed (as for OAuth accounts). Re-enabling safely requires:
#   1. A transactional email provider (e.g. Resend) to confirm the NEW address
#      before the change applies.
#   2. Server-side re-authentication of the current password (same pattern as
#      update_password below) — a stolen JWT must not be able to swap the email
#      and seize the account.
#   3. Syncing user_profiles.email alongside the Supabase auth update so the
#      app-level row and the auth row never diverge.
# AuthService.update_email is left in place as the building block for (3).
#
# @router.put("/email", response_model=MessageResponse)
# @limiter.limit("10/minute")
# async def update_email(
#     request: Request,
#     body: UpdateEmailRequest,
#     claims: CurrentUserClaims,
#     auth_service: AuthSvc,
# ) -> MessageResponse:
#     """Initiate an email change via the Supabase admin API."""
#     if not await auth_service.verify_password(claims.email, body.current_password):
#         raise AppValidationError("Current password is incorrect")
#     await auth_service.update_email(uuid.UUID(claims.sub), str(body.new_email))
#     return MessageResponse(
#         message="Email update initiated.",
#         detail="Check your new address for a confirmation link.",
#     )


@router.put("/password", response_model=MessageResponse)
@limiter.limit("10/minute")
async def update_password(
    request: Request,
    body: UpdatePasswordRequest,
    claims: CurrentUserClaims,
    auth_service: AuthSvc,
) -> MessageResponse:
    """Update the authenticated user's password via the Supabase admin API.

    Re-authenticates with the current password first. A valid JWT alone must not be
    enough to rotate the password — otherwise a stolen token grants full account
    takeover. The current-password check is enforced here, server-side, not just in
    the UI (which an attacker calling the API directly would bypass).
    """
    if not await auth_service.verify_password(claims.email, body.current_password):
        raise AppValidationError("Current password is incorrect")
    await auth_service.update_password(uuid.UUID(claims.sub), body.new_password)
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

    Order: clean up sole-owned orgs (OrgService) → soft-delete profile (UserService)
    → delete Supabase auth (AuthService).

    Failure modes:
    - If org cleanup fails: nothing changed, user still has full access.
    - If profile soft-delete fails after org cleanup: orphaned org rows remain but
      user can still log in and contact support. No Stripe subscriptions are orphaned
      because org deletion cascades subscription rows at the DB level.
    - If Supabase auth delete fails after DB is cleared: user has no profile or
      memberships so they cannot access any data. The orphaned Supabase auth record
      means re-login still issues a JWT, but upsert_from_supabase raises AccountDeletedError
      — the user sees "contact support" and cannot access anything.

    body.confirmation must equal "DELETE MY ACCOUNT".

    Production pattern: replace with status=pending_deletion and enqueue a background
    job to hard-delete, cancel Stripe, purge storage, and remove from email lists
    asynchronously with retries after a grace period.

    """
    await org_service.cleanup_for_deleted_user(user_id)
    await service.delete(user_id)
    await auth_service.delete_user(user_id)
    return MessageResponse(
        message="Account deleted.",
        detail="All your data has been permanently removed.",
    )
