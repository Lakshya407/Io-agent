"""Authentication request/response schemas."""

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    """Login payload (OAuth2 compatible username field)."""

    username: EmailStr = Field(..., examples=["admin@example.com"])
    password: str = Field(..., min_length=1, examples=["secret"])


class RegisterRequest(BaseModel):
    """Registration payload."""

    email: EmailStr = Field(..., examples=["user@example.com"])
    password: str = Field(..., min_length=8, examples=["strong-password"])
    name: str = Field(..., min_length=1, max_length=255, examples=["User"])


class RefreshRequest(BaseModel):
    """Refresh token payload."""

    refresh_token: str = Field(...)


class TokenResponse(BaseModel):
    """JWT pair returned by login/register/refresh."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(..., examples=[1800])


class TokenPayload(BaseModel):
    """Decoded JWT claims used internally by the security layer."""

    sub: str
    exp: int
    type: str
