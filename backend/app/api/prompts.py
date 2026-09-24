"""Prompt management router (admin-only).

CRUD over system prompts; the active default prompt replaces the built-in
chat system instruction. Endpoint contracts are documented in docs/API.md.
"""

from uuid import UUID

from fastapi import APIRouter, Query, status

from app.core.dependencies import CurrentAdmin, DBSession, PaginationParams
from app.schemas.common import PaginatedResponse
from app.schemas.prompt import PromptCreate, PromptOut, PromptUpdate
from app.services.prompt_service import PromptService

router = APIRouter(tags=["prompts"])


@router.get(
    "",
    response_model=PaginatedResponse[PromptOut],
    summary="List prompts",
    operation_id="prompts_list",
)
async def prompts_list(
    admin: CurrentAdmin,
    db: DBSession,
    pagination: PaginationParams,
    active_only: bool = Query(
        default=False, description="Only return prompts with status=active"
    ),
) -> PaginatedResponse[PromptOut]:
    """One page of prompts, newest first (admin only)."""
    items, total = await PromptService(db).list_prompts(
        pagination.offset, pagination.page_size, active_only=active_only
    )
    return PaginatedResponse(
        items=[PromptOut.model_validate(item) for item in items],
        page=pagination.page,
        page_size=pagination.page_size,
        total=total,
    )


@router.post(
    "",
    response_model=PromptOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a prompt",
    operation_id="prompts_create",
)
async def prompts_create(
    admin: CurrentAdmin,
    db: DBSession,
    payload: PromptCreate,
) -> PromptOut:
    """Register a new prompt (admin only). Names are unique."""
    prompt = await PromptService(db).create_prompt(payload)
    return PromptOut.model_validate(prompt)


@router.get(
    "/{prompt_id}",
    response_model=PromptOut,
    summary="Read a prompt",
    operation_id="prompts_get",
)
async def prompts_get(
    admin: CurrentAdmin,
    db: DBSession,
    prompt_id: UUID,
) -> PromptOut:
    """Fetch one prompt by id (admin only)."""
    prompt = await PromptService(db).get_prompt(prompt_id)
    return PromptOut.model_validate(prompt)


@router.patch(
    "/{prompt_id}",
    response_model=PromptOut,
    summary="Update a prompt",
    operation_id="prompts_update",
)
async def prompts_update(
    admin: CurrentAdmin,
    db: DBSession,
    prompt_id: UUID,
    payload: PromptUpdate,
) -> PromptOut:
    """Partially update a prompt — status, content, default flag, etc."""
    prompt = await PromptService(db).update_prompt(prompt_id, payload)
    return PromptOut.model_validate(prompt)


@router.delete(
    "/{prompt_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a prompt",
    operation_id="prompts_delete",
)
async def prompts_delete(
    admin: CurrentAdmin,
    db: DBSession,
    prompt_id: UUID,
) -> None:
    """Remove a prompt from the catalog (admin only)."""
    await PromptService(db).delete_prompt(prompt_id)
