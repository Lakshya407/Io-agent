"""User schemas (request/response models for the users API)."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models import UserRole


class UserOut(BaseModel):
    """Public user representation (never exposes ``password_hash``)."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr
    name: str
    role: UserRole
    is_active: bool
    created_at: datetime
    updated_at: datetime


class UserMeUpdate(BaseModel):
    """Payload for PUT /api/v1/users/me."""

    name: str | None = Field(None, min_length=1, max_length=255)
    email: EmailStr | None = None


class UserAdminUpdate(BaseModel):
    """Payload for PATCH /api/v1/users/{user_id} (admin only)."""

    name: str | None = Field(None, min_length=1, max_length=255)
    email: EmailStr | None = None
    role: UserRole | None = None
    is_active: bool | None = None


class UserCreate(BaseModel):
    """Payload for admin-initiated user creation."""

    email: EmailStr
    password: str = Field(..., min_length=8)
    name: str = Field(..., min_length=1, max_length=255)
    role: UserRole = UserRole.USER
