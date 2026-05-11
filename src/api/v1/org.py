"""Org endpoints — organisation CRUD and member management."""

# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Standard Library
import uuid

# Third Party
from fastapi import APIRouter, Request

# Internal
from src.core.dependencies import CurrentUserID, OrgSvc
from src.core.middleware.rate_limit import limiter
from src.schemas.common import MessageResponse
from src.schemas.org.requests import (
    CreateOrgRequest,
    InviteMemberRequest,
    UpdateMemberRoleRequest,
    UpdateOrgRequest,
)
from src.schemas.org.responses import MemberResponse, OrgResponse

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #

router = APIRouter(prefix="/orgs", tags=["Organisations"])


@router.post("", response_model=OrgResponse, status_code=201)
@limiter.limit("10/minute")
async def create_org(
    request: Request,
    body: CreateOrgRequest,
    user_id: CurrentUserID,
    service: OrgSvc,
) -> OrgResponse:
    """Create a new organisation. The caller becomes the owner automatically."""
    org = await service.create_org(user_id, name=body.name, slug=body.slug)
    return OrgResponse.model_validate(org)


@router.get("", response_model=list[OrgResponse])
@limiter.limit("60/minute")
async def list_my_orgs(
    request: Request,
    user_id: CurrentUserID,
    service: OrgSvc,
) -> list[OrgResponse]:
    """List all orgs the authenticated user is an active member of."""
    orgs = await service.list_my_orgs(user_id)
    return [OrgResponse.model_validate(o) for o in orgs]


@router.get("/{org_id}", response_model=OrgResponse)
@limiter.limit("60/minute")
async def get_org(
    request: Request,
    org_id: uuid.UUID,
    user_id: CurrentUserID,
    service: OrgSvc,
) -> OrgResponse:
    """Return org details. User must be an active member."""
    org = await service.get_org(org_id, user_id)
    return OrgResponse.model_validate(org)


@router.patch("/{org_id}", response_model=OrgResponse)
@limiter.limit("20/minute")
async def update_org(
    request: Request,
    org_id: uuid.UUID,
    body: UpdateOrgRequest,
    user_id: CurrentUserID,
    service: OrgSvc,
) -> OrgResponse:
    """Update org display name. Requires admin or owner role."""
    org = await service.update_org(org_id, user_id, name=body.name)
    return OrgResponse.model_validate(org)


@router.get("/{org_id}/members", response_model=list[MemberResponse])
@limiter.limit("60/minute")
async def list_members(
    request: Request,
    org_id: uuid.UUID,
    user_id: CurrentUserID,
    service: OrgSvc,
) -> list[MemberResponse]:
    """List active members of an org. User must be a member."""
    return await service.list_members(org_id, user_id)


@router.post("/{org_id}/members", response_model=MemberResponse, status_code=201)
@limiter.limit("20/minute")
async def invite_member(
    request: Request,
    org_id: uuid.UUID,
    body: InviteMemberRequest,
    user_id: CurrentUserID,
    service: OrgSvc,
) -> MemberResponse:
    """Invite an existing user to the org by email. Requires admin or owner role."""
    membership = await service.invite_member(
        org_id, inviter_id=user_id, email=str(body.email), role=body.role
    )
    return MemberResponse.model_validate(membership)


@router.post("/{org_id}/members/accept", response_model=MemberResponse)
@limiter.limit("20/minute")
async def accept_invite(
    request: Request,
    org_id: uuid.UUID,
    user_id: CurrentUserID,
    service: OrgSvc,
) -> MemberResponse:
    """Accept a pending org invite for the authenticated user."""
    membership = await service.accept_invite(org_id, user_id)
    return MemberResponse.model_validate(membership)


@router.patch("/{org_id}/members/{target_user_id}", response_model=MemberResponse)
@limiter.limit("20/minute")
async def update_member_role(
    request: Request,
    org_id: uuid.UUID,
    target_user_id: uuid.UUID,
    body: UpdateMemberRoleRequest,
    user_id: CurrentUserID,
    service: OrgSvc,
) -> MemberResponse:
    """Change a member's role. Only owners can perform this."""
    membership = await service.change_role(
        org_id,
        requester_id=user_id,
        target_user_id=target_user_id,
        new_role=body.role,
    )
    return MemberResponse.model_validate(membership)


@router.delete("/{org_id}/members/{target_user_id}", response_model=MessageResponse)
@limiter.limit("20/minute")
async def remove_member(
    request: Request,
    org_id: uuid.UUID,
    target_user_id: uuid.UUID,
    user_id: CurrentUserID,
    service: OrgSvc,
) -> MessageResponse:
    """Remove a member from the org. Requires admin or owner role."""
    await service.remove_member(org_id, requester_id=user_id, target_user_id=target_user_id)
    return MessageResponse(message="Member removed.")
