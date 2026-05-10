"""BaseRepository — generic async CRUD base for all repositories."""

# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Standard Library
import uuid
from datetime import datetime, timezone
from typing import Any, Generic, TypeVar

# Third Party
from sqlalchemy import func, select, true
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import SQLModel

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #

ModelT = TypeVar("ModelT", bound=SQLModel)


class BaseRepository(Generic[ModelT]):
    """Generic async CRUD base. Subclass and set model_class.

    Args:
        session (AsyncSession): The active database session.

    """

    model_class: type[ModelT]

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ── Create ────────────────────────────────────────────────

    async def create(self, obj: ModelT) -> ModelT:
        """Persist a new record and return it with DB-generated fields populated."""
        self.session.add(obj)
        await self.session.flush()
        await self.session.refresh(obj)
        return obj

    async def create_many(self, objs: list[ModelT]) -> list[ModelT]:
        """Persist multiple records in a single flush."""
        self.session.add_all(objs)
        await self.session.flush()
        for obj in objs:
            await self.session.refresh(obj)
        return objs

    # ── Read ──────────────────────────────────────────────────

    async def get_by_id(self, id: uuid.UUID) -> ModelT | None:
        """Fetch a single record by primary key, excluding soft-deleted rows."""
        stmt = (
            select(self.model_class)
            .where(self.model_class.id == id)  # type: ignore[attr-defined]
            .where(self._not_deleted())
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_many(
        self,
        *,
        filters: list[Any] | None = None,
        order_by: Any | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ModelT]:
        """Fetch a filtered, ordered page of records."""
        stmt = select(self.model_class).where(self._not_deleted())
        if filters:
            stmt = stmt.where(*filters)
        if order_by is not None:
            stmt = stmt.order_by(order_by)
        stmt = stmt.limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count(self, *filters: Any) -> int:
        """Count records matching optional filters, excluding soft-deleted rows."""
        stmt = (
            select(func.count())
            .select_from(self.model_class)
            .where(self._not_deleted())
        )
        if filters:
            stmt = stmt.where(*filters)
        result = await self.session.execute(stmt)
        return result.scalar_one()

    # ── Update ────────────────────────────────────────────────

    async def update(self, obj: ModelT, **fields: Any) -> ModelT:
        """Apply field updates to an existing record and flush."""
        for key, value in fields.items():
            setattr(obj, key, value)
        self.session.add(obj)
        await self.session.flush()
        await self.session.refresh(obj)
        return obj

    # ── Delete ────────────────────────────────────────────────

    async def soft_delete(self, obj: ModelT) -> ModelT:
        """Mark a record as deleted without removing it from the database."""
        return await self.update(obj, deleted_at=datetime.now(timezone.utc))

    async def hard_delete(self, obj: ModelT) -> None:
        """Permanently remove a record. Use only for GDPR wipe — prefer soft_delete."""
        await self.session.delete(obj)
        await self.session.flush()

    # ── Helpers ───────────────────────────────────────────────

    def _not_deleted(self) -> Any:
        if hasattr(self.model_class, "deleted_at"):
            return self.model_class.deleted_at.is_(None)  # type: ignore[attr-defined]
        return true()
