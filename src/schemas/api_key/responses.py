"""API key response schemas."""

# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Standard Library
import uuid
from datetime import datetime
from typing import Optional

# Third Party
from pydantic import BaseModel, Field

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #


class ApiKeyResponse(BaseModel):
    """API key metadata — raw key is never returned after creation."""

    model_config = {"from_attributes": True}

    id: uuid.UUID = Field(description="Unique key identifier.")
    name: str = Field(description="Human-readable label for the key.")
    key_prefix: str = Field(description="First 11 chars of the raw key shown for identification e.g. 'sk_abc12345x'.")
    created_at: datetime = Field(description="UTC timestamp when the key was created.")
    expires_at: Optional[datetime] = Field(description="UTC expiry time; null = never expires.")
    last_used_at: Optional[datetime] = Field(description="UTC timestamp of most recent use; null if never used.")


class ApiKeyCreatedResponse(ApiKeyResponse):
    """Returned once at creation — includes the raw key that must be saved now."""

    raw_key: str = Field(description="Full API key shown once at creation; store securely, never retrievable again.")
