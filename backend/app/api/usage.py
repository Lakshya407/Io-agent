"""Usage router: personal usage + usage history.

Endpoint contracts are documented in docs/API.md.
"""

from datetime import datetime

from fastapi import APIRouter, Query

from app.core.dependencies import CurrentUser, DBSession, PaginationParams
from app.schemas.common import PaginatedResponse
from app.schemas.usage import UsageHistoryItem, UsageOut
from app.services.usage_service import UsageService

router = APIRouter(tags=["usage"])


@router.get(
    "",
    response_model=UsageOut,
    summary="Get my current usage",
    operation_id="usage_get",
)
async def get_usage(
    current_user: CurrentUser,
    db: DBSession,
) -> UsageOut:
    """Return the authenticated user's monthly allowance summary."""
    allowance = await UsageService(db).get_usage(current_user.id)
    return UsageOut.model_validate(allowance)


@router.get(
    "/history",
    response_model=PaginatedResponse[UsageHistoryItem],
    summary="Get my usage history",
    operation_id="usage_history",
)
async def get_usage_history(
    current_user: CurrentUser,
    db: DBSession,
    pagination: PaginationParams,
    model: str | None = Query(None, description="Filter by model name"),
    provider: str | None = Query(None, description="Filter by provider"),
    date_from: datetime | None = Query(None, description="Inclusive lower bound"),
    date_to: datetime | None = Query(None, description="Inclusive upper bound"),
) -> PaginatedResponse[UsageHistoryItem]:
    """Aggregated daily usage for the user, filterable via query parameters."""
    items, total = await UsageService(db).history(
        user_id=current_user.id,
        offset=pagination.offset,
        limit=pagination.page_size,
        model=model,
        provider=provider,
        date_from=date_from,
        date_to=date_to,
    )
    return PaginatedResponse[UsageHistoryItem](
        items=items,
        page=pagination.page,
        page_size=pagination.page_size,
        total=total,
    )


__all__ = ["router"]
