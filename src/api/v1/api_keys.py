"""API key endpoints — create, list, and revoke org API keys."""

# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Standard Library
import uuid

# Third Party
from fastapi import APIRouter, Request

# Internal
from src.core.dependencies import ApiKeySvc, AuditSvc, CurrentUserID
from src.core.middleware.rate_limit import limiter
from src.schemas.api_key.requests import CreateApiKeyRequest
from src.schemas.api_key.responses import ApiKeyCreatedResponse, ApiKeyResponse
from src.schemas.common import MessageResponse

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #

router = APIRouter(prefix="/orgs/{org_id}/api-keys", tags=["API Keys"])


@router.get("", response_model=list[ApiKeyResponse])
@limiter.limit("60/minute")
async def list_api_keys(
    request: Request,
    org_id: uuid.UUID,
    user_id: CurrentUserID,
    service: ApiKeySvc,
) -> list[ApiKeyResponse]:
    """Return all active API keys for an org. Requires admin role."""
    return await service.list_keys(org_id, user_id)


@router.post("", response_model=ApiKeyCreatedResponse, status_code=201)
@limiter.limit("10/minute")
async def create_api_key(
    request: Request,
    org_id: uuid.UUID,
    body: CreateApiKeyRequest,
    user_id: CurrentUserID,
    service: ApiKeySvc,
    audit: AuditSvc,
) -> ApiKeyCreatedResponse:
    """Create a new API key. The raw key is returned once — store it securely. Requires admin role."""
    result = await service.create(org_id, user_id, name=body.name, expires_at=body.expires_at)
    await audit.log_event(
        org_id=org_id,
        action="api_key.created",
        resource_type="api_key",
        actor_id=user_id,
        resource_id=str(result.id),
        metadata={"name": body.name},
    )
    return result


@router.delete("/{key_id}", response_model=MessageResponse)
@limiter.limit("10/minute")
async def revoke_api_key(
    request: Request,
    org_id: uuid.UUID,
    key_id: uuid.UUID,
    user_id: CurrentUserID,
    service: ApiKeySvc,
    audit: AuditSvc,
) -> MessageResponse:
    """Revoke an API key immediately. Requires admin role."""
    await service.revoke(org_id, user_id, key_id)
    await audit.log_event(
        org_id=org_id,
        action="api_key.revoked",
        resource_type="api_key",
        actor_id=user_id,
        resource_id=str(key_id),
    )
    return MessageResponse(message="API key revoked.")
