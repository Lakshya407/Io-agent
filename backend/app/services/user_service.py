"""User service: profile management and admin user management.

Every method performs a single database interaction and commits, keeping the
API layer free of business logic and SQL.
"""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictException, not_found
from app.models.user import User
from app.schemas.user import UserAdminUpdate, UserMeUpdate


class UserService:
    """CRUD operations over users."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_users(
        self, offset: int, limit: int
    ) -> tuple[list[User], int]:
        """Return one page of users (newest first) plus the total count."""
        total = await self.db.scalar(select(func.count()).select_from(User))

        result = await self.db.execute(
            select(User)
            .order_by(User.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all()), int(total or 0)

    async def get_user(self, user_id: UUID) -> User:
        """Return a user or raise a 404."""
        return await self._get_or_404(user_id)

    async def update_me(self, user: User, data: UserMeUpdate) -> User:
        """Update the profile of the currently authenticated user."""
        if data.email is not None and data.email != user.email:
            await self._assert_email_available(data.email)
            user.email = data.email
        if data.name is not None:
            user.name = data.name

        await self.db.commit()
        # Reload DB-generated values (e.g. ``updated_at``) before returning —
        # expired attributes cannot be lazily loaded during response validation.
        await self.db.refresh(user)
        return user

    async def admin_update_user(
        self, user_id: UUID, data: UserAdminUpdate
    ) -> User:
        """Admin-only update of any user's profile, role or status."""
        user = await self._get_or_404(user_id)

        if data.email is not None and data.email != user.email:
            await self._assert_email_available(data.email)
            user.email = data.email
        if data.name is not None:
            user.name = data.name
        if data.role is not None:
            user.role = data.role
        if data.is_active is not None:
            user.is_active = data.is_active

        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def delete_user(self, user_id: UUID) -> None:
        """Delete a user (cascades to conversations, keys and allowance)."""
        user = await self._get_or_404(user_id)
        await self.db.delete(user)
        await self.db.commit()

    async def _get_or_404(self, user_id: UUID) -> User:
        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if user is None:
            raise not_found("User", user_id)
        return user

    async def _assert_email_available(self, email: str) -> None:
        existing = await self.db.execute(select(User).where(User.email == email))
        if existing.scalar_one_or_none() is not None:
            raise ConflictException(
                f"A user with email {email} is already registered.",
                code="EMAIL_ALREADY_REGISTERED",
            )
