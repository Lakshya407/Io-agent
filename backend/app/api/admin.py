"""Admin router: dashboard, users, usage, models, tools, audit logs.

Every endpoint requires an administrator. Endpoint contracts are documented
in docs/API.md.
"""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Request, status
from sqlalchemy import func, select

from app.core.dependencies import CurrentAdmin, DBSession, PaginationParams
from app.models.audit_log import AuditAction, AuditLog
from app.schemas.admin import AuditLogOut, DashboardStats
from app.schemas.common import PaginatedResponse
from app.schemas.model import ModelCreate, ModelOut, ModelStatusUpdate, ModelUpdate
from app.schemas.tool import ToolCreate, ToolOut, ToolStatusUpdate, ToolUpdate
from app.schemas.usage import AdminUsageRow, AllowanceUpdate, UsageOut
from app.schemas.user import UserOut
from app.services.audit_service import AuditService
from app.services.admin_service import get_dashboard_stats
from app.services.model_service import ModelService
from app.services.tool_service import ToolService
from app.services.usage_service import UsageService
from app.services.user_service import UserService

router = APIRouter(tags=["admin"])


def _client_ip(request: Request) -> str | None:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


@router.get(
    "/dashboard",
    response_model=DashboardStats,
    summary="Platform dashboard statistics",
    operation_id="admin_dashboard",
)
async def dashboard(
    admin: CurrentAdmin,
    db: DBSession,
) -> DashboardStats:
    """Aggregated statistics for the admin overview page."""
    return await get_dashboard_stats(db)


@router.get(
    "/users",
    response_model=PaginatedResponse[UserOut],
    summary="List all users",
    operation_id="admin_users_list",
)
async def list_users(
    admin: CurrentAdmin,
    db: DBSession,
    pagination: PaginationParams,
) -> PaginatedResponse[UserOut]:
    """Return one page of all users."""
    users, total = await UserService(db).list_users(
        offset=pagination.offset, limit=pagination.page_size
    )
    return PaginatedResponse[UserOut](
        items=[UserOut.model_validate(u) for u in users],
        page=pagination.page,
        page_size=pagination.page_size,
        total=total,
    )


@router.get(
    "/usage",
    response_model=PaginatedResponse[AdminUsageRow],
    summary="List usage for all users",
    operation_id="admin_usage_list",
)
async def list_usage(
    admin: CurrentAdmin,
    db: DBSession,
    pagination: PaginationParams,
) -> PaginatedResponse[AdminUsageRow]:
    """Return one page of every user's allowance."""
    rows, total = await UsageService(db).admin_list_usage(
        offset=pagination.offset, limit=pagination.page_size
    )
    return PaginatedResponse[AdminUsageRow](
        items=rows,
        page=pagination.page,
        page_size=pagination.page_size,
        total=total,
    )


@router.get(
    "/usage/{user_id}",
    response_model=UsageOut,
    summary="Get usage for a user",
    operation_id="admin_usage_get",
)
async def get_usage(
    user_id: UUID,
    admin: CurrentAdmin,
    db: DBSession,
) -> UsageOut:
    """Return a specific user's allowance summary."""
    allowance = await UsageService(db).get_usage(user_id)
    return UsageOut.model_validate(allowance)


@router.patch(
    "/users/{user_id}/allowance",
    response_model=UsageOut,
    summary="Update a user's allowance",
    operation_id="admin_allowance_update",
)
async def update_allowance(
    user_id: UUID,
    data: AllowanceUpdate,
    admin: CurrentAdmin,
    db: DBSession,
    request: Request,
) -> UsageOut:
    """Configure a user's monthly token/request limits."""
    allowance = await UsageService(db).admin_update_allowance(user_id, data)
    await AuditService(db).log(
        action=AuditAction.USAGE_LIMIT_UPDATED,
        resource_type="user",
        resource_id=str(user_id),
        user_id=admin.id,
        ip_address=_client_ip(request),
        user_agent=request.headers.get("user-agent"),
        metadata=data.model_dump(mode="json", exclude_none=True),
    )
    await db.commit()
    return UsageOut.model_validate(allowance)


# --- Model management ---------------------------------------------------


@router.post(
    "/models",
    response_model=ModelOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a model",
    operation_id="admin_models_create",
)
async def create_model(
    data: ModelCreate,
    admin: CurrentAdmin,
    db: DBSession,
    request: Request,
) -> ModelOut:
    """Register a new model in the catalog."""
    model = await ModelService(db).create_model(data)
    await AuditService(db).log(
        action=AuditAction.MODEL_CREATED,
        resource_type="model",
        resource_id=str(model.id),
        user_id=admin.id,
        ip_address=_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )
    await db.commit()
    return ModelOut.model_validate(model)


@router.put(
    "/models/{model_id}",
    response_model=ModelOut,
    summary="Update a model",
    operation_id="admin_models_update",
)
async def update_model(
    model_id: UUID,
    data: ModelUpdate,
    admin: CurrentAdmin,
    db: DBSession,
    request: Request,
) -> ModelOut:
    """Update a model's configuration."""
    model = await ModelService(db).update_model(model_id, data)
    await AuditService(db).log(
        action=AuditAction.MODEL_UPDATED,
        resource_type="model",
        resource_id=str(model.id),
        user_id=admin.id,
        ip_address=_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )
    await db.commit()
    return ModelOut.model_validate(model)


@router.patch(
    "/models/{model_id}/status",
    response_model=ModelOut,
    summary="Enable or disable a model",
    operation_id="admin_models_status",
)
async def set_model_status(
    model_id: UUID,
    data: ModelStatusUpdate,
    admin: CurrentAdmin,
    db: DBSession,
    request: Request,
) -> ModelOut:
    """Enable or disable a model without changing its other settings."""
    model = await ModelService(db).set_status(model_id, data)
    await AuditService(db).log(
        action=(
            AuditAction.MODEL_DISABLED if not data.is_active else AuditAction.MODEL_UPDATED
        ),
        resource_type="model",
        resource_id=str(model.id),
        user_id=admin.id,
        ip_address=_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )
    await db.commit()
    return ModelOut.model_validate(model)


@router.delete(
    "/models/{model_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a model",
    operation_id="admin_models_delete",
)
async def delete_model(
    model_id: UUID,
    admin: CurrentAdmin,
    db: DBSession,
    request: Request,
) -> None:
    """Remove a model from the catalog."""
    await ModelService(db).delete_model(model_id)
    await AuditService(db).log(
        action=AuditAction.MODEL_DISABLED,
        resource_type="model",
        resource_id=str(model_id),
        user_id=admin.id,
        ip_address=_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )
    await db.commit()


# --- Tool management ----------------------------------------------------


@router.post(
    "/tools",
    response_model=ToolOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a tool",
    operation_id="admin_tools_create",
)
async def create_tool(
    data: ToolCreate,
    admin: CurrentAdmin,
    db: DBSession,
    request: Request,
) -> ToolOut:
    """Register a new tool in the catalog."""
    tool = await ToolService(db).create_tool(data)
    await AuditService(db).log(
        action=AuditAction.TOOL_CREATED,
        resource_type="tool",
        resource_id=str(tool.id),
        user_id=admin.id,
        ip_address=_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )
    await db.commit()
    return ToolOut.model_validate(tool)


@router.put(
    "/tools/{tool_id}",
    response_model=ToolOut,
    summary="Update a tool",
    operation_id="admin_tools_update",
)
async def update_tool(
    tool_id: UUID,
    data: ToolUpdate,
    admin: CurrentAdmin,
    db: DBSession,
    request: Request,
) -> ToolOut:
    """Update a tool's configuration."""
    tool = await ToolService(db).update_tool(tool_id, data)
    await AuditService(db).log(
        action=AuditAction.TOOL_UPDATED,
        resource_type="tool",
        resource_id=str(tool.id),
        user_id=admin.id,
        ip_address=_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )
    await db.commit()
    return ToolOut.model_validate(tool)


@router.patch(
    "/tools/{tool_id}/status",
    response_model=ToolOut,
    summary="Enable or disable a tool",
    operation_id="admin_tools_status",
)
async def set_tool_status(
    tool_id: UUID,
    data: ToolStatusUpdate,
    admin: CurrentAdmin,
    db: DBSession,
    request: Request,
) -> ToolOut:
    """Enable or disable a tool."""
    tool = await ToolService(db).set_status(tool_id, data)
    await AuditService(db).log(
        action=(
            AuditAction.TOOL_DISABLED if not data.is_active else AuditAction.TOOL_UPDATED
        ),
        resource_type="tool",
        resource_id=str(tool.id),
        user_id=admin.id,
        ip_address=_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )
    await db.commit()
    return ToolOut.model_validate(tool)


@router.delete(
    "/tools/{tool_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a tool",
    operation_id="admin_tools_delete",
)
async def delete_tool(
    tool_id: UUID,
    admin: CurrentAdmin,
    db: DBSession,
    request: Request,
) -> None:
    """Remove a tool from the catalog."""
    await ToolService(db).delete_tool(tool_id)
    await AuditService(db).log(
        action=AuditAction.TOOL_DISABLED,
        resource_type="tool",
        resource_id=str(tool_id),
        user_id=admin.id,
        ip_address=_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )
    await db.commit()


# --- Audit logs ---------------------------------------------------------


@router.get(
    "/audit-logs",
    response_model=PaginatedResponse[AuditLogOut],
    summary="List audit logs",
    operation_id="admin_audit_logs",
)
async def list_audit_logs(
    admin: CurrentAdmin,
    db: DBSession,
    pagination: PaginationParams,
    action: AuditAction | None = Query(None, description="Filter by action"),
    resource_type: str | None = Query(None, description="Filter by resource type"),
    user_id: UUID | None = Query(None, description="Filter by actor"),
) -> PaginatedResponse[AuditLogOut]:
    """Return one page of immutable audit events (newest first)."""
    conditions = []
    if action is not None:
        conditions.append(AuditLog.action == action)
    if resource_type is not None:
        conditions.append(AuditLog.resource_type == resource_type)
    if user_id is not None:
        conditions.append(AuditLog.user_id == user_id)

    count_stmt = select(func.count()).select_from(AuditLog)
    list_stmt = select(AuditLog)
    for condition in conditions:
        count_stmt = count_stmt.where(condition)
        list_stmt = list_stmt.where(condition)

    total = await db.scalar(count_stmt)
    result = await db.execute(
        list_stmt.order_by(AuditLog.created_at.desc())
        .offset(pagination.offset)
        .limit(pagination.page_size)
    )
    logs = list(result.scalars().all())

    return PaginatedResponse[AuditLogOut](
        items=[AuditLogOut.model_validate(log) for log in logs],
        page=pagination.page,
        page_size=pagination.page_size,
        total=int(total or 0),
    )


__all__ = ["router"]
