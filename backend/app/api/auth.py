"""Authentication router: register / login / refresh / me.

Endpoint contracts are documented in docs/API.md.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm

from app.core.dependencies import DBSession, CurrentUser
from app.core.rate_limit import rate_limit
from app.schemas.auth import LoginRequest, RefreshRequest, RegisterRequest, TokenResponse
from app.schemas.user import UserOut
from app.services.auth_service import AuthService

router = APIRouter(tags=["auth"])


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    operation_id="register",
)
async def register(
    data: RegisterRequest,
    db: DBSession,
    _: Annotated[None, Depends(rate_limit)],
) -> TokenResponse:
    """Create a standard user account and return a token pair."""
    _user, tokens = await AuthService(db).register(data)
    return tokens


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login and obtain tokens",
    operation_id="login",
)
async def login(
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: DBSession,
    _: Annotated[None, Depends(rate_limit)],
) -> TokenResponse:
    """Authenticate with email/password (OAuth2 form for /docs compatibility)."""
    return await AuthService(db).login(
        LoginRequest(username=form.username, password=form.password)
    )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refresh the access token",
    operation_id="refresh",
)
async def refresh(
    data: RefreshRequest,
    db: DBSession,
    _: Annotated[None, Depends(rate_limit)],
) -> TokenResponse:
    """Exchange a refresh token for a new token pair."""
    return await AuthService(db).refresh(data)


@router.get(
    "/me",
    response_model=UserOut,
    summary="Get the current user",
    operation_id="auth_me",
)
async def me(current_user: CurrentUser) -> UserOut:
    """Return the profile of the authenticated user."""
    return UserOut.model_validate(current_user)


__all__ = ["router"]
