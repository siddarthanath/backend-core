"""Audit log response schemas."""

# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Standard Library
import uuid
from datetime import datetime
from typing import Optional

# Third Party
from pydantic import BaseModel, Field

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #


class AuditLogResponse(BaseModel):
    """Single audit event."""

    model_config = {"from_attributes": True}

    id: uuid.UUID = Field(description="Unique record identifier.")
    org_id: uuid.UUID = Field(description="Org this event belongs to.")
    actor_id: Optional[uuid.UUID] = Field(description="User who triggered the action; null for system-generated events.")
    action: str = Field(description="Dot-notation event name e.g. 'api_key.created'.")
    resource_type: str = Field(description="Entity type acted on e.g. 'api_key'.")
    resource_id: Optional[str] = Field(description="Stringified ID of the affected entity.")
    event_metadata: Optional[dict[str, object]] = Field(description="Arbitrary event-specific context.")
    created_at: datetime = Field(description="UTC timestamp when the event was recorded.")


class AuditLogListResponse(BaseModel):
    """Paginated audit event list."""

    items: list[AuditLogResponse] = Field(description="Page of audit events.")
    total: int = Field(description="Total matching events across all pages.")
    limit: int = Field(description="Max results returned per page.")
    offset: int = Field(description="Number of results skipped before this page.")
