"""User request schemas — validated input for user endpoints."""

# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Third Party
from pydantic import BaseModel, EmailStr, field_validator

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #

_CONFIRMATION_PHRASE = "DELETE MY ACCOUNT"


class UpdateProfileRequest(BaseModel):
    """Update display name fields. All fields optional — only provided fields are updated."""

    first_name: str | None = None
    last_name: str | None = None


class UpdateEmailRequest(BaseModel):
    """Request to update the authenticated user's email via Supabase admin."""

    new_email: EmailStr


class UpdatePasswordRequest(BaseModel):
    """Request to update the authenticated user's password via Supabase admin."""

    new_password: str

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        """Enforce minimum password length."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class RequestPasswordResetRequest(BaseModel):
    """Public endpoint — triggers Supabase to email a password reset link."""

    email: EmailStr


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
