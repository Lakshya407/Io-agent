"""Tool router: list/read tools (public to authenticated users).

Admin tool management lives under /api/v1/admin/tools. Endpoint contracts are
documented in docs/API.md.
"""

from uuid import UUID

from fastapi import APIRouter, Query

from app.core.dependencies import CurrentUser, DBSession, PaginationParams
from app.schemas.common import PaginatedResponse
from app.schemas.tool import ToolOut
from app.services.tool_service import ToolService

router = APIRouter(tags=["tools"])


@router.get(
    "",
    response_model=PaginatedResponse[ToolOut],
    summary="List available tools",
    operation_id="tools_list",
)
async def list_tools(
    current_user: CurrentUser,
    db: DBSession,
    pagination: PaginationParams,
    active_only: bool = Query(
        True, description="Set to false to include disabled tools"
    ),
) -> PaginatedResponse[ToolOut]:
    """Return the catalog of tools agents may use."""
    tools, total = await ToolService(db).list_tools(
        offset=pagination.offset,
        limit=pagination.page_size,
        active_only=active_only,
    )
    return PaginatedResponse[ToolOut](
        items=[ToolOut.model_validate(t) for t in tools],
        page=pagination.page,
        page_size=pagination.page_size,
        total=total,
    )


@router.get(
    "/{tool_id}",
    response_model=ToolOut,
    summary="Get a tool",
    operation_id="tools_get",
)
async def get_tool(
    tool_id: UUID,
    current_user: CurrentUser,
    db: DBSession,
) -> ToolOut:
    """Return a single tool configuration."""
    tool = await ToolService(db).get_tool(tool_id)
    return ToolOut.model_validate(tool)


__all__ = ["router"]
