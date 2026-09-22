"""User router: profile management + admin user management.

Endpoint contracts are documented in docs/API.md.
"""

from typing import Annotated

from fastapi import APIRouter, status

from app.core.dependencies import CurrentAdmin, CurrentUser, DBSession, PaginationParams
from app.core.exceptions import not_found
from app.models.audit_log import AuditAction
from app.schemas.common import PaginatedResponse
from app.schemas.user import UserAdminUpdate, UserMeUpdate, UserOut
from app.services.audit_service import AuditService
from app.services.user_service import UserService

router = APIRouter(tags=["users"])


@router.get(
    "/me",
    response_model=UserOut,
    summary="Get my profile",
    operation_id="users_get_me",
)
async def get_me(current_user: CurrentUser) -> UserOut:
    """Return the profile of the authenticated user."""
    return UserOut.model_validate(current_user)


@router.put(
    "/me",
    response_model=UserOut,
    summary="Update my profile",
    operation_id="users_update_me",
)
async def update_me(
    data: UserMeUpdate,
    current_user: CurrentUser,
    db: DBSession,
) -> UserOut:
    """Update the name or email of the authenticated user."""
    user = await UserService(db).update_me(current_user, data)
    return UserOut.model_validate(user)


@router.get(
    "",
    response_model=PaginatedResponse[UserOut],
    summary="List users (admin)",
    operation_id="users_list",
)
async def list_users(
    admin: CurrentAdmin,
    db: DBSession,
    pagination: PaginationParams,
) -> PaginatedResponse[UserOut]:
    """Return one page of all users (administrators only)."""
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
    "/{user_id}",
    response_model=UserOut,
    summary="Get a user (admin)",
    operation_id="users_get",
)
async def get_user(
    user_id: str,
    admin: CurrentAdmin,
    db: DBSession,
) -> UserOut:
    """Return any user by id (administrators only)."""
    user = await UserService(db).get_user(_as_uuid(user_id))
    return UserOut.model_validate(user)


@router.patch(
    "/{user_id}",
    response_model=UserOut,
    summary="Update a user (admin)",
    operation_id="users_update",
)
async def update_user(
    user_id: str,
    data: UserAdminUpdate,
    admin: CurrentAdmin,
    db: DBSession,
) -> UserOut:
    """Update a user's profile, role or status (administrators only)."""
    user = await UserService(db).admin_update_user(_as_uuid(user_id), data)
    await AuditService(db).log(
        action=AuditAction.USER_UPDATED,
        resource_type="user",
        resource_id=str(user.id),
        user_id=admin.id,
    )
    await db.commit()
    return UserOut.model_validate(user)


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a user (admin)",
    operation_id="users_delete",
)
async def delete_user(
    user_id: str,
    admin: CurrentAdmin,
    db: DBSession,
) -> None:
    """Delete a user and their data (administrators only)."""
    target_id = _as_uuid(user_id)
    await UserService(db).delete_user(target_id)
    await AuditService(db).log(
        action=AuditAction.USER_DELETED,
        resource_type="user",
        resource_id=str(target_id),
        user_id=admin.id,
    )
    await db.commit()


def _as_uuid(value: str):
    """Parse a path parameter into a UUID, raising 404 on malformed input."""
    from uuid import UUID

    try:
        return UUID(value)
    except ValueError:
        raise not_found("User", value) from None


__all__ = ["router"]
