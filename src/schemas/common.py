"""Common response schemas — reusable envelope types used across all domains."""

# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Standard Library
from typing import Generic, TypeVar

# Third Party
from pydantic import BaseModel

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #

T = TypeVar("T")


class PaginationMeta(BaseModel):
    """Pagination metadata included in every paginated response."""

    total: int
    limit: int
    offset: int
    has_more: bool


class PaginatedResponse(BaseModel, Generic[T]):
    """Wraps a list of items with pagination metadata.

    Usage: response_model=PaginatedResponse[MyItemResponse]

    """

    data: list[T]
    meta: PaginationMeta


class MessageResponse(BaseModel):
    """Generic success response for operations that have no meaningful return value."""

    message: str
    detail: str | None = None
