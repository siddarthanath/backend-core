"""Feature flag request schemas."""

# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Standard Library
from typing import Optional

# Third Party
from pydantic import BaseModel, Field

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #


class UpsertFlagRequest(BaseModel):
    """Create or update a feature flag for an org."""

    key: str = Field(
        min_length=1,
        max_length=100,
        pattern=r"^[a-z0-9_]+$",
        description="Snake_case identifier e.g. 'new_billing_ui'; must be unique per org.",
    )
    enabled: bool = Field(description="Whether the flag is active.")
    description: Optional[str] = Field(
        default=None,
        max_length=300,
        description="Optional human-readable note about the flag's purpose.",
    )
