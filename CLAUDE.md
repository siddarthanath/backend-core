# backend-core — Claude Code Instructions

## Code Style

### File Structure (Python)
Every file must follow this exact structure:

```python
"""One-line description of what this file does."""

# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Standard Library
import os
from typing import Optional

# Third Party
from fastapi import APIRouter

# Internal
from src.utils.logging import setup_logger

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #

logger = setup_logger(__name__)
```

Rules:
- File docstring: one line, describes the file's purpose
- Imports: always in three groups with the exact headers above (omit a group if empty)
- `setup_logger(__name__)` at the top of code section if the file logs anything
- No blank lines between import groups beyond one line

### Docstrings
All public functions and classes must have a docstring in this format:

```python
def my_function(arg1: str, arg2: int) -> list[str]:
    """Short one-line summary.

    Args:
        arg1 (str): Description of arg1.
        arg2 (int): Description of arg2.

    Raises:
        ValueError: When arg1 is empty.

    Returns:
        list[str]: Description of return value.

    """
```

Rules:
- First line: short summary, no period at end
- Blank line after summary
- Args/Raises/Returns sections only when non-trivial
- Closing `"""` on its own line

### Typing
- All function signatures must have full type annotations (args + return type)
- Never use `Any` — use `object`, `Unknown`, or a proper type
- Use `X | Y` union syntax (not `Union[X, Y]`)
- Use `list[X]`, `dict[K, V]` (not `List[X]`, `Dict[K, V]`) — except in `Generic` class bodies

### Logging
- Use `setup_logger(__name__)` from `src.utils.logging`
- No `print()` statements anywhere
- Log at appropriate levels: `DEBUG` for tracing, `INFO` for lifecycle events, `WARNING` for unexpected-but-recoverable, `ERROR` for failures

### No-nos
- No bare `except:` — always catch specific exceptions
- No mutable default arguments
- No circular imports — use `TYPE_CHECKING` guard for type-only imports
- No hardcoded strings for config (URLs, secrets, limits) — always from `get_settings()`

## Layer Rules

| Layer | Location | Rule |
|---|---|---|
| DB models | `src/models/` | SQLModel `table=True` only. Never returned directly from handlers. |
| API schemas | `src/schemas/` | Pydantic `BaseModel` only. One file per domain. |
| Settings | `src/configs/settings/` | Pydantic `BaseSettings`. All config from env. |
| Handlers | `src/api/v1/` | Thin — validate → call service → return schema. No business logic. |
| Services | `src/services/` | Business logic. Takes Pydantic in, returns Pydantic out. |
| Repositories | `src/repositories/` | DB queries only. Returns SQLModel instances. |

Every endpoint must declare `response_model=XResponse`. No `dict`, no `Any` returns.

## Registry

Module-level typed registries in `src/core/registry.py`:
- `db_registry` — database session factory
- Add new registries here as product features require them (e.g., `llm_registry`)

Never instantiate services or sessions inside request handlers — always resolve from a registry.

## Logging Roadmap

Currently using stdlib `logging` (simple, zero deps). Migration to `structlog` planned for Round 3 to enable:
- JSON structured logs in production
- Request ID propagation via context vars
- User ID binding in middleware

Do not add structlog until Round 3.

Most importantly, make sure to not waffle in your responses. I require clear analytical responses in a way that I learn but also efficiently code.