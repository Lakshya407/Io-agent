"""Chat schemas (request/response models for the chat API)."""

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class MessageRole(StrEnum):
    """Role of a message in a conversation."""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class ChatMessage(BaseModel):
    """A single message in a chat exchange."""

    role: MessageRole
    content: str = Field(..., min_length=1)


class ChatRequest(BaseModel):
    """Payload for POST /api/v1/chat."""

    message: str = Field(..., min_length=1, examples=["Hello"])
    conversation_id: UUID | None = Field(
        default=None, description="Reuse an existing conversation"
    )
    model: str | None = Field(default=None, description="Model name override")


class TokenUsageSchema(BaseModel):
    """Token accounting for a chat response."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class ChatResponseMessage(BaseModel):
    """The assistant message returned by POST /api/v1/chat."""

    role: MessageRole = MessageRole.ASSISTANT
    content: str


class ChatResponse(BaseModel):
    """Response for POST /api/v1/chat."""

    conversation_id: UUID
    message: ChatResponseMessage
    model: str
    usage: TokenUsageSchema


class ConversationSummary(BaseModel):
    """Summary of a conversation for list endpoints."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    created_at: datetime
    updated_at: datetime


class MessageOut(BaseModel):
    """A stored message returned by the messages endpoint."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    role: MessageRole
    content: str
    model: str | None = None
    total_tokens: int = 0
    created_at: datetime
