"""Chat router: chat completion + conversations.

Endpoint contracts are documented in docs/API.md.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.core.dependencies import CurrentUser, DBSession, PaginationParams
from app.core.rate_limit import rate_limit
from app.schemas.chat import (
    ChatRequest,
    ChatResponse,
    ConversationSummary,
    MessageOut,
)
from app.schemas.common import PaginatedResponse
from app.services.chat_service import ChatService

router = APIRouter(tags=["chat"])


@router.post(
    "/chat",
    response_model=ChatResponse,
    summary="Send a message and get a reply",
    operation_id="chat",
)
async def chat(
    data: ChatRequest,
    current_user: CurrentUser,
    db: DBSession,
    _: Annotated[None, Depends(rate_limit)],
) -> ChatResponse:
    """Run the full chat flow (usage check → mock LLM → persistence)."""
    return await ChatService(db).chat(current_user, data)


@router.get(
    "/conversations",
    response_model=PaginatedResponse[ConversationSummary],
    summary="List my conversations",
    operation_id="conversations_list",
)
async def list_conversations(
    current_user: CurrentUser,
    db: DBSession,
    pagination: PaginationParams,
) -> PaginatedResponse[ConversationSummary]:
    """Return one page of the user's conversations."""
    conversations, total = await ChatService(db).list_conversations(
        user_id=current_user.id,
        offset=pagination.offset,
        limit=pagination.page_size,
    )
    return PaginatedResponse[ConversationSummary](
        items=[ConversationSummary.model_validate(c) for c in conversations],
        page=pagination.page,
        page_size=pagination.page_size,
        total=total,
    )


@router.get(
    "/conversations/{conversation_id}",
    response_model=ConversationSummary,
    summary="Get a conversation",
    operation_id="conversations_get",
)
async def get_conversation(
    conversation_id: UUID,
    current_user: CurrentUser,
    db: DBSession,
) -> ConversationSummary:
    """Return one conversation belonging to the authenticated user."""
    conversation = await ChatService(db).get_conversation(
        current_user.id, conversation_id
    )
    return ConversationSummary.model_validate(conversation)


@router.get(
    "/conversations/{conversation_id}/messages",
    response_model=PaginatedResponse[MessageOut],
    summary="List messages in a conversation",
    operation_id="conversations_messages",
)
async def list_messages(
    conversation_id: UUID,
    current_user: CurrentUser,
    db: DBSession,
    pagination: PaginationParams,
) -> PaginatedResponse[MessageOut]:
    """Return one page of messages from a conversation, oldest first."""
    messages, total = await ChatService(db).get_messages(
        user_id=current_user.id,
        conversation_id=conversation_id,
        offset=pagination.offset,
        limit=pagination.page_size,
    )
    return PaginatedResponse[MessageOut](
        items=[MessageOut.model_validate(m) for m in messages],
        page=pagination.page,
        page_size=pagination.page_size,
        total=total,
    )


@router.delete(
    "/conversations/{conversation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a conversation",
    operation_id="conversations_delete",
)
async def delete_conversation(
    conversation_id: UUID,
    current_user: CurrentUser,
    db: DBSession,
) -> None:
    """Delete a conversation and all of its messages."""
    await ChatService(db).delete_conversation(current_user.id, conversation_id)


__all__ = ["router"]
