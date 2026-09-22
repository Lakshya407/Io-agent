"""Chat router: chat completion + streaming + conversations.

Endpoint contracts are documented in docs/API.md.
"""

import asyncio
import json
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import StreamingResponse

from app.core.dependencies import CurrentUser, DBSession, PaginationParams
from app.core.logging import get_logger
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
logger = get_logger(__name__)


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


def _sse_frame(event: str, data: dict) -> str:
    """Format one SSE frame with JSON data."""
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


@router.post(
    "/chat/stream",
    summary="Stream a reply with Server-Sent Events",
    operation_id="chat_stream",
)
async def chat_stream(
    data: ChatRequest,
    current_user: CurrentUser,
    db: DBSession,
    request: Request,
    _: Annotated[None, Depends(rate_limit)],
) -> StreamingResponse:
    """Stream the assistant reply token-by-token over SSE.

    Events: ``activity`` → ``message_start`` → ``token``* →
    ``message_complete`` (or ``error``). The browser must talk only to this
    endpoint — never to Ollama directly.
    """
    # Ownership is validated BEFORE the SSE response starts so unknown or
    # foreign conversations return a clean 404 instead of failing mid-stream
    # ("response already started").
    if data.conversation_id is not None:
        await ChatService(db).get_conversation(
            current_user.id, data.conversation_id
        )
    service = ChatService(db)

    async def event_source():
        stream = service.stream_chat(current_user, data)
        try:
            async for item in stream:
                if await request.is_disconnected():
                    logger.info("SSE client disconnected; stopping stream")
                    await stream.aclose()
                    break
                yield _sse_frame(item["event"], item["data"])
        except (asyncio.CancelledError, GeneratorExit):
            # Client hit Stop — the service persists the partial reply.
            logger.info("SSE stream cancelled by client")
            try:
                await stream.aclose()
            except Exception:
                pass
            raise

    return StreamingResponse(
        event_source(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


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
