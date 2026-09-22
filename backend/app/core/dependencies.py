"""Shared FastAPI dependencies: DB session, Redis, auth, pagination."""

from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends, Query
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenException, UnauthorizedException
from app.core.logging import user_id_ctx
from app.core.redis import get_redis
from app.core.security import ACCESS_TOKEN_TYPE, decode_token
from app.database.connection import get_db
from app.models import UserRole
from app.models.user import User
from redis.asyncio import Redis

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

DBSession = Annotated[AsyncSession, Depends(get_db)]
RedisClient = Annotated[Redis, Depends(get_redis)]


class Pagination:
    """Pagination query params shared by every collection endpoint."""

    def __init__(
        self,
        page: Annotated[int, Query(ge=1, description="Page number")] = 1,
        page_size: Annotated[
            int, Query(ge=1, le=100, description="Items per page (max 100)")
        ] = 20,
    ) -> None:
        self.page = page
        self.page_size = page_size

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: DBSession,
) -> User:
    """Resolve the JWT bearer token to the active user (401 otherwise)."""
    payload = decode_token(token, expected_type=ACCESS_TOKEN_TYPE)
    user_id = payload["sub"]

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise UnauthorizedException("User no longer exists.", code="USER_NOT_FOUND")
    if not user.is_active:
        raise UnauthorizedException("User account is disabled.", code="USER_DISABLED")

    user_id_ctx.set(str(user.id))
    return user


async def get_current_admin(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Require an administrator (403 for normal users)."""
    if current_user.role != UserRole.ADMIN:
        raise ForbiddenException("Administrator privileges are required.")
    return current_user


CurrentUser = Annotated[User, Depends(get_current_user)]
CurrentAdmin = Annotated[User, Depends(get_current_admin)]
PaginationParams = Annotated[Pagination, Depends()]

# Same scheme, but does not fail when the token is missing/invalid — used by
# the rate limiter so public endpoints (login/register) can be limited by IP.
oauth2_scheme_optional = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login", auto_error=False
)


async def get_optional_user(
    token: Annotated[str | None, Depends(oauth2_scheme_optional)],
    db: DBSession,
) -> User | None:
    """Resolve the bearer token if present; otherwise return ``None``."""
    if not token:
        return None
    try:
        payload = decode_token(token, expected_type=ACCESS_TOKEN_TYPE)
    except UnauthorizedException:
        return None

    result = await db.execute(select(User).where(User.id == payload["sub"]))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        return None

    user_id_ctx.set(str(user.id))
    return user
