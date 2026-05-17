"""Feature flag response schemas."""

# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Standard Library
import uuid
from typing import Optional

# Third Party
from pydantic import BaseModel, Field

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #


class FeatureFlagResponse(BaseModel):
    """Single feature flag."""

    model_config = {"from_attributes": True}

    id: uuid.UUID = Field(description="Unique flag identifier.")
    org_id: uuid.UUID = Field(description="Org this flag belongs to.")
    key: str = Field(description="Snake_case identifier e.g. 'new_billing_ui'.")
    enabled: bool = Field(description="Current on/off state of the flag.")
    description: Optional[str] = Field(description="Optional human-readable note about the flag's purpose.")
