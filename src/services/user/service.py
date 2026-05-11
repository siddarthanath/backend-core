"""UserService — profile lifecycle: create, read, update, soft-delete."""

# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Standard Library
import uuid

# Internal
from src.core.exceptions.types import NotFoundError
from src.models.user import UserProfile
from src.repositories.user import UserRepository

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #


class UserService:
    """Orchestrates UserProfile operations. Raises typed exceptions, never HTTPException."""

    def __init__(self, repo: UserRepository) -> None:
        self.repo = repo

    async def get_or_create(self, user_id: uuid.UUID, email: str) -> UserProfile:
        """Return existing profile or create one from Supabase auth data.

        Args:
            user_id (uuid.UUID): Supabase auth UUID (sub claim).
            email (str): Email from the verified JWT.

        Returns:
            UserProfile: The existing or newly created profile.

        """
        return await self.repo.upsert_from_supabase(user_id=user_id, email=email)

    async def get_me(self, user_id: uuid.UUID) -> UserProfile:
        """Fetch the authenticated user's profile.

        Args:
            user_id (uuid.UUID): The authenticated user's UUID.

        Raises:
            NotFoundError: If no profile exists for the given user_id.

        Returns:
            UserProfile: The user's profile record.

        """
        user = await self.repo.get_by_id(user_id)
        if not user:
            raise NotFoundError("User", user_id)
        return user

    async def update_profile(
        self,
        user_id: uuid.UUID,
        first_name: str | None = None,
        last_name: str | None = None,
    ) -> UserProfile:
        """Update display name fields — only provided (non-None) fields are changed.

        Args:
            user_id (uuid.UUID): The authenticated user's UUID.
            first_name (str | None): New first name, or None to leave unchanged.
            last_name (str | None): New last name, or None to leave unchanged.

        Returns:
            UserProfile: The updated profile record.

        """
        user = await self.get_me(user_id)
        updates: dict[str, str] = {}
        if first_name is not None:
            updates["first_name"] = first_name
        if last_name is not None:
            updates["last_name"] = last_name
        return await self.repo.update(user, **updates)

    async def delete(self, user_id: uuid.UUID) -> None:
        """Soft-delete the user's profile. Auth deletion is handled by AuthService.

        Args:
            user_id (uuid.UUID): The authenticated user's UUID.

        Raises:
            NotFoundError: If no profile exists for the given user_id.

        """
        user = await self.get_me(user_id)
        await self.repo.soft_delete(user)
