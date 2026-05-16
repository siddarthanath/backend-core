"""API key request schemas."""

# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Standard Library
from datetime import datetime
from typing import Optional

# Third Party
from pydantic import BaseModel, Field

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #


class CreateApiKeyRequest(BaseModel):
    """Create a new API key for an org."""

    name: str = Field(
        min_length=1,
        max_length=100,
        description="Human-readable label for the key e.g. 'CI Pipeline'.",
    )
    expires_at: Optional[datetime] = Field(
        default=None,
        description="Optional UTC datetime after which the key is invalid; null = never expires.",
    )
