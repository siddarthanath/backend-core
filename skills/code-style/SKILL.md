# Skill: Python Code Style

Reference for consistent code style in backend-core. See also `CLAUDE.md` at repo root.

## File Structure

```python
"""One-line description of what this file does."""

# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Standard Library
from typing import Optional

# Third Party
from fastapi import APIRouter

# Internal
from src.utils.logging import setup_logger

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #

logger = setup_logger(__name__)
```

## Docstring Format

```python
def function(arg1: str, arg2: int) -> list[str]:
    """Short summary.

    Args:
        arg1 (str): Description.
        arg2 (int): Description.

    Raises:
        ValueError: When condition.

    Returns:
        list[str]: Description.

    """
```

## Typing Rules

- Full annotations on all functions (args + return)
- `X | Y` not `Union[X, Y]`
- `list[X]`, `dict[K, V]` not `List`, `Dict`
- No `Any` — use specific types or `object`
- `TYPE_CHECKING` guard for type-only imports to avoid circular deps

## Logging

```python
# At top of file (after imports)
logger = setup_logger(__name__)

# Usage
logger.info("Session started.")
logger.warning("Unexpected state, continuing.")
logger.error("Failed to connect.")
```

No `print()`. No bare `except:`.

## Common Patterns

### Handler (thin)
```python
@router.get("/items/{item_id}", response_model=ItemResponse)
async def get_item(
    item_id: uuid.UUID,
    session: DBSession,
    user_id: CurrentUserID,
) -> ItemResponse:
    """Get a single item by ID."""
    return await item_service.get(session, item_id, user_id)
```

### Service (business logic)
```python
async def get(session: AsyncSession, item_id: uuid.UUID, user_id: uuid.UUID) -> ItemResponse:
    """Fetch item and verify ownership.

    Args:
        session (AsyncSession): Database session.
        item_id (uuid.UUID): ID of the item to fetch.
        user_id (uuid.UUID): ID of the requesting user.

    Raises:
        NotFoundError: If item does not exist.
        ForbiddenError: If user does not own the item.

    Returns:
        ItemResponse: The item data.

    """
    item = await item_repo.get_by_id(session, item_id)
    if not item:
        raise NotFoundError("Item", item_id)
    if item.user_id != user_id:
        raise ForbiddenError("Not your item.")
    return ItemResponse.model_validate(item)
```