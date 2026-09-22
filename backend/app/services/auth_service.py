"""Authentication service: registration, login and token refresh.

All business logic lives here — the API layer only validates input, calls
this service and returns the response schema.
"""

from fastapi import status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import ConflictException, UnauthorizedException
from app.core.security import (
    ACCESS_TOKEN_TYPE,
    REFRESH_TOKEN_TYPE,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models import UserRole
from app.models.user import User
from app.schemas.auth import LoginRequest, RefreshRequest, RegisterRequest, TokenResponse
from app.schemas.user import UserOut
from app.services.audit_service import AuditService
from app.services.usage_service import UsageService


class AuthService:
    """Handles credentials, JWT issuance and first-run provisioning."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.audit = AuditService(db)
        self.usage = UsageService(db)

    async def register(self, data: RegisterRequest) -> tuple[UserOut, TokenResponse]:
        """Register a new standard user and provision their allowance."""
        existing = await self.db.execute(
            select(User).where(User.email == data.email)
        )
        if existing.scalar_one_or_none() is not None:
            raise ConflictException(
                f"A user with email {data.email} is already registered.",
                code="EMAIL_ALREADY_REGISTERED",
            )

        user = User(
            email=data.email,
            password_hash=hash_password(data.password),
            name=data.name,
            role=UserRole.USER,
        )
        self.db.add(user)
        await self.db.flush()  # populate user.id

        await self.usage.create_for_user(user.id)
        await self.audit.log(
            action="USER_CREATED",
            resource_type="user",
            resource_id=str(user.id),
            user_id=user.id,
        )
        await self.db.commit()

        return UserOut.model_validate(user), self._issue_tokens(user)

    async def login(self, data: LoginRequest) -> TokenResponse:
        """Authenticate by email/password and return a fresh token pair.

        The error is identical for an unknown email and a wrong password so
        the endpoint cannot be used to enumerate accounts.
        """
        result = await self.db.execute(select(User).where(User.email == data.username))
        user = result.scalar_one_or_none()

        if user is None or not verify_password(data.password, user.password_hash):
            raise UnauthorizedException(
                "Invalid email or password.", code="INVALID_CREDENTIALS"
            )
        if not user.is_active:
            raise UnauthorizedException(
                "User account is disabled.", code="USER_DISABLED"
            )

        await self.audit.log(
            action="USER_LOGIN",
            resource_type="user",
            resource_id=str(user.id),
            user_id=user.id,
        )
        await self.db.commit()

        return self._issue_tokens(user)

    async def refresh(self, data: RefreshRequest) -> TokenResponse:
        """Exchange a valid refresh token for a new token pair."""
        payload = decode_token(data.refresh_token, expected_type=REFRESH_TOKEN_TYPE)

        result = await self.db.execute(select(User).where(User.id == payload["sub"]))
        user = result.scalar_one_or_none()
        if user is None:
            raise UnauthorizedException("User no longer exists.", code="USER_NOT_FOUND")
        if not user.is_active:
            raise UnauthorizedException("User account is disabled.", code="USER_DISABLED")

        return self._issue_tokens(user)

    def _issue_tokens(self, user: User) -> TokenResponse:
        """Build the access + refresh JWT pair for a user."""
        access_token = create_access_token(
            str(user.id), extra_claims={"role": user.role.value}
        )
        refresh_token = create_refresh_token(str(user.id))
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.access_token_expire_minutes * 60,
        )
