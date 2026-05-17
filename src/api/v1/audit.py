"""Audit log endpoints — read-only access to org audit events."""

# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Standard Library
import uuid

# Third Party
from fastapi import APIRouter, Query, Request

# Internal
from src.core.dependencies import AuditSvc, CurrentUserID
from src.core.middleware.rate_limit import limiter
from src.schemas.audit.responses import AuditLogListResponse

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #

router = APIRouter(prefix="/orgs/{org_id}/audit-log", tags=["Audit"])


@router.get("", response_model=AuditLogListResponse)
@limiter.limit("60/minute")
async def list_audit_events(
    request: Request,
    org_id: uuid.UUID,
    user_id: CurrentUserID,
    service: AuditSvc,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> AuditLogListResponse:
    """Return paginated audit events for an org. Requires admin or owner role."""
    return await service.get_events(org_id, user_id, limit=limit, offset=offset)
