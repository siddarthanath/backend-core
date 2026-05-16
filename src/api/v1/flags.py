"""Feature flag endpoints — manage and evaluate org feature toggles."""

# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Standard Library
import uuid

# Third Party
from fastapi import APIRouter, Request

# Internal
from src.core.dependencies import CurrentUserID, FlagSvc
from src.core.middleware.rate_limit import limiter
from src.schemas.common import MessageResponse
from src.schemas.flag.requests import UpsertFlagRequest
from src.schemas.flag.responses import FeatureFlagResponse

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #

router = APIRouter(prefix="/orgs/{org_id}/flags", tags=["Feature Flags"])


@router.get("", response_model=list[FeatureFlagResponse])
@limiter.limit("120/minute")
async def list_flags(
    request: Request,
    org_id: uuid.UUID,
    user_id: CurrentUserID,
    service: FlagSvc,
) -> list[FeatureFlagResponse]:
    """Return all feature flags for an org. Requires member role."""
    return await service.get_flags(org_id, user_id)


@router.post("", response_model=FeatureFlagResponse, status_code=201)
@limiter.limit("30/minute")
async def upsert_flag(
    request: Request,
    org_id: uuid.UUID,
    body: UpsertFlagRequest,
    user_id: CurrentUserID,
    service: FlagSvc,
) -> FeatureFlagResponse:
    """Create or update a feature flag for an org. Requires admin role."""
    return await service.upsert(
        org_id,
        user_id,
        key=body.key,
        enabled=body.enabled,
        description=body.description,
    )


@router.delete("/{flag_id}", response_model=MessageResponse)
@limiter.limit("30/minute")
async def delete_flag(
    request: Request,
    org_id: uuid.UUID,
    flag_id: uuid.UUID,
    user_id: CurrentUserID,
    service: FlagSvc,
) -> MessageResponse:
    """Delete a feature flag. Requires admin role."""
    await service.delete(org_id, user_id, flag_id)
    return MessageResponse(message="Feature flag deleted.")
