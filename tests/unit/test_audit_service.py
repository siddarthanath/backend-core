"""Unit tests for AuditService — no database, all repositories mocked."""

# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Standard Library
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

# Third Party
import pytest

# Internal
from src.core.exceptions.types import ForbiddenError, NotFoundError
from src.repositories.audit import AuditRepository
from src.repositories.org import MembershipRepository, OrgRepository
from src.services.audit.service import AuditService

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #


def make_service(*, repo=None, org_repo=None, membership_repo=None):
    repo = repo or AsyncMock(spec=AuditRepository)
    org_repo = org_repo or AsyncMock(spec=OrgRepository)
    membership_repo = membership_repo or AsyncMock(spec=MembershipRepository)
    return AuditService(repo=repo, org_repo=org_repo, membership_repo=membership_repo), repo, org_repo, membership_repo


def make_log(**kwargs):
    entry = MagicMock()
    entry.id = kwargs.get("id", uuid.uuid4())
    entry.org_id = kwargs.get("org_id", uuid.uuid4())
    entry.actor_id = kwargs.get("actor_id", None)
    entry.action = kwargs.get("action", "api_key.created")
    entry.resource_type = kwargs.get("resource_type", "api_key")
    entry.resource_id = kwargs.get("resource_id", None)
    entry.event_metadata = kwargs.get("event_metadata", None)
    entry.created_at = kwargs.get("created_at", datetime.now(timezone.utc))
    entry.updated_at = kwargs.get("updated_at", datetime.now(timezone.utc))
    return entry


@pytest.mark.asyncio
async def test_log_event_persists_and_returns_response():
    svc, repo, _, _ = make_service()
    org_id = uuid.uuid4()
    actor_id = uuid.uuid4()
    stored = make_log(org_id=org_id, actor_id=actor_id, action="member.invited", resource_type="member")
    repo.create.return_value = stored

    result = await svc.log_event(
        org_id=org_id,
        action="member.invited",
        resource_type="member",
        actor_id=actor_id,
        resource_id="abc123",
        metadata={"email": "x@y.com"},
    )

    repo.create.assert_called_once()
    assert result.org_id == org_id
    assert result.actor_id == actor_id
    assert result.action == "member.invited"


@pytest.mark.asyncio
async def test_log_event_allows_null_actor_for_system_events():
    svc, repo, _, _ = make_service()
    stored = make_log(actor_id=None, action="system.cleanup")
    repo.create.return_value = stored

    result = await svc.log_event(org_id=uuid.uuid4(), action="system.cleanup", resource_type="system")
    assert result.actor_id is None


@pytest.mark.asyncio
async def test_get_events_returns_paginated_list():
    svc, repo, org_repo, membership_repo = make_service()
    org_id = uuid.uuid4()
    user_id = uuid.uuid4()
    org_repo.get_by_id.return_value = MagicMock(id=org_id)
    membership_repo.user_has_role.return_value = True
    logs = [make_log(org_id=org_id), make_log(org_id=org_id)]
    repo.get_by_org.return_value = logs
    repo.count_by_org.return_value = 2

    result = await svc.get_events(org_id, user_id, limit=10, offset=0)

    assert result.total == 2
    assert len(result.items) == 2
    assert result.limit == 10
    assert result.offset == 0


@pytest.mark.asyncio
async def test_get_events_raises_not_found_for_unknown_org():
    svc, _, org_repo, _ = make_service()
    org_repo.get_by_id.return_value = None

    with pytest.raises(NotFoundError):
        await svc.get_events(uuid.uuid4(), uuid.uuid4())


@pytest.mark.asyncio
async def test_get_events_raises_forbidden_for_non_admin():
    svc, _, org_repo, membership_repo = make_service()
    org_repo.get_by_id.return_value = MagicMock()
    membership_repo.user_has_role.return_value = False

    with pytest.raises(ForbiddenError):
        await svc.get_events(uuid.uuid4(), uuid.uuid4())
