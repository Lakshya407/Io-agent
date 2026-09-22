"""Shared response schemas (error envelope + pagination)."""

from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ErrorDetail(BaseModel):
    """Machine-readable error information."""

    code: str = Field(..., examples=["USER_NOT_FOUND"])
    message: str = Field(..., examples=["User not found"])


class ErrorResponse(BaseModel):
    """The single error envelope returned by every failing endpoint."""

    success: bool = Field(default=False)
    error: ErrorDetail
    request_id: str = Field(..., examples=["abc-123"])


class PaginatedResponse(BaseModel, Generic[T]):
    """Paginated list response used by every collection endpoint."""

    items: list[T]
    page: int = Field(..., ge=1, examples=[1])
    page_size: int = Field(..., ge=1, le=100, examples=[20])
    total: int = Field(..., ge=0, examples=[100])
