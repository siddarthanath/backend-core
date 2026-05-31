"""Feature flag response schemas."""

# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Standard Library
import uuid

# Third-Party Library
from pydantic import BaseModel, Field

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #


class FeatureFlagResponse(BaseModel):
    """Single feature flag."""

    model_config = {"from_attributes": True}

    id: uuid.UUID = Field(description="Unique flag identifier.")
    org_id: uuid.UUID = Field(description="Org this flag belongs to.")
    key: str = Field(description="Snake_case identifier e.g. 'new_billing_ui'.")
    enabled: bool = Field(description="Current on/off state of the flag.")
    description: str | None = Field(
        description="Optional human-readable note about the flag's purpose."
    )
