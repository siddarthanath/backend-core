"""AuditRepository — read/write access for audit_logs table."""

# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Standard Library
import uuid

# Third Party
from sqlalchemy import select

# Internal
from src.models.audit import AuditLog
from src.repositories.base import BaseRepository

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #


class AuditRepository(BaseRepository[AuditLog]):
    """Repository for audit log records. Insert-only — no update or delete."""

    model_class = AuditLog

    async def get_by_org(
        self,
        org_id: uuid.UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> list[AuditLog]:
        """Return audit events for an org, newest first.

        Args:
            org_id (uuid.UUID): The org's UUID.
            limit (int): Max records to return. Defaults to 50.
            offset (int): Records to skip. Defaults to 0.

        Returns:
            list[AuditLog]: Matching audit events.

        """
        stmt = (
            select(AuditLog)
            .where(AuditLog.org_id == org_id)
            .order_by(AuditLog.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count_by_org(self, org_id: uuid.UUID) -> int:
        """Return total audit event count for an org.

        Args:
            org_id (uuid.UUID): The org's UUID.

        Returns:
            int: Total event count.

        """
        from sqlalchemy import func
        stmt = (
            select(func.count())
            .select_from(AuditLog)
            .where(AuditLog.org_id == org_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()
