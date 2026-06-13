"""User request schemas — validated input for user endpoints."""

# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Third-Party Library
from pydantic import BaseModel, EmailStr, field_validator

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #

_CONFIRMATION_PHRASE = "DELETE MY ACCOUNT"


class UpdateProfileRequest(BaseModel):
    """Update display name fields. All fields optional — only provided fields are updated."""

    first_name: str | None = None
    last_name: str | None = None


class UpdateEmailRequest(BaseModel):
    """Request to update the authenticated user's email via Supabase admin.

    The email-change endpoint is disabled in this template (see api/v1/user.py).
    current_password is included so the re-enabled endpoint can re-authenticate
    before changing the email — same pattern as UpdatePasswordRequest.
    """

    current_password: str
    new_email: EmailStr


class UpdatePasswordRequest(BaseModel):
    """Request to update the authenticated user's password via Supabase admin.

    current_password is re-verified server-side before the change — a valid JWT
    alone must not be enough to rotate the password (see H1 in FINDINGS.md).
    """

    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        """Mirror the frontend PASSWORD_RULES from src/lib/auth/password.ts."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not any(c.isupper() for c in v):
            raise ValueError(
                "Password must contain at least one uppercase letter (A–Z)"
            )
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one number (0–9)")
        if not any(not c.isalnum() for c in v):
            raise ValueError("Password must contain at least one special character")
        return v


class DeleteAccountRequest(BaseModel):
    """Requires explicit confirmation phrase to prevent accidental deletion."""

    confirmation: str

    @field_validator("confirmation")
    @classmethod
    def must_confirm(cls, v: str) -> str:
        """Validate the explicit confirmation phrase."""
        if v != _CONFIRMATION_PHRASE:
            raise ValueError(f"confirmation must be '{_CONFIRMATION_PHRASE}'")
        return v
