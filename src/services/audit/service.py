"""AuditService — write and query org-level audit events."""

# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Standard Library
import uuid
from typing import Optional

# Internal
from src.core.exceptions.types import ForbiddenError, NotFoundError
from src.models.audit import AuditLog
from src.repositories.audit import AuditRepository
from src.repositories.org import MembershipRepository, OrgRepository
from src.schemas.audit.responses import AuditLogListResponse, AuditLogResponse
from src.utils.logging import get_logger

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #

log = get_logger(__name__)


class AuditService:
    """Write and query audit events. Callers are responsible for supplying actor_id."""

    def __init__(
        self,
        repo: AuditRepository,
        org_repo: OrgRepository,
        membership_repo: MembershipRepository,
    ) -> None:
        self.repo = repo
        self.org_repo = org_repo
        self.membership_repo = membership_repo

    async def log_event(
        self,
        org_id: uuid.UUID,
        action: str,
        resource_type: str,
        actor_id: Optional[uuid.UUID] = None,
        resource_id: Optional[str] = None,
        metadata: Optional[dict[str, object]] = None,
    ) -> AuditLogResponse:
        """Append an audit event for an org.

        Args:
            org_id (uuid.UUID): The org to log against.
            action (str): Dot-notation action string (e.g. "api_key.created").
            resource_type (str): Type of affected resource (e.g. "api_key").
            actor_id (uuid.UUID | None): User who performed the action; None for system events.
            resource_id (str | None): ID of the affected resource.
            metadata (dict | None): Additional structured context.

        Returns:
            AuditLogResponse: The created audit event.

        """
        entry = AuditLog(
            org_id=org_id,
            actor_id=actor_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            event_metadata=metadata,
        )
        created = await self.repo.create(entry)
        log.info("audit.event_logged", org_id=str(org_id), action=action)
        return AuditLogResponse.model_validate(created)

    async def get_events(
        self,
        org_id: uuid.UUID,
        user_id: uuid.UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> AuditLogListResponse:
        """Return paginated audit events for an org.

        Args:
            org_id (uuid.UUID): The org's UUID.
            user_id (uuid.UUID): Requesting user — must be admin or owner.
            limit (int): Max records to return. Defaults to 50.
            offset (int): Records to skip. Defaults to 0.

        Raises:
            NotFoundError: If the org does not exist.
            ForbiddenError: If the user is not an admin or owner.

        Returns:
            AuditLogListResponse: Paginated list of audit events.

        """
        org = await self.org_repo.get_by_id(org_id)
        if not org:
            raise NotFoundError("Organisation", org_id)
        from src.constants import Role
        if not await self.membership_repo.user_has_role(user_id, org_id, Role.ADMIN):
            raise ForbiddenError("Only admins can view the audit log")

        events = await self.repo.get_by_org(org_id, limit=limit, offset=offset)
        total = await self.repo.count_by_org(org_id)
        return AuditLogListResponse(
            items=[AuditLogResponse.model_validate(e) for e in events],
            total=total,
            limit=limit,
            offset=offset,
        )
