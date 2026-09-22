"""Chat service: conversation management and message completion.

Implements the flow required by ``POST /api/v1/chat``:

    authentication → usage check → create/reuse conversation → resolve model
    → persist user message → LLM provider (Ollama by default) → persist reply
    → record usage → response

Conversation history is loaded from PostgreSQL and passed to the provider on
every request, so follow-up questions keep their context.
"""

import time
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import (
    ServiceUnavailableException,
    UsageLimitExceededException,
    ValidationException,
    not_found,
)
from app.core.logging import get_logger
from app.llm.base import (
    LLMModelNotFoundError,
    LLMProvider,
    LLMProviderError,
    LLMResponse,
)
from app.llm.factory import get_llm_provider
from app.models import MessageRole
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.user import User
from app.schemas.chat import (
    ChatMessage,
    ChatRequest,
    ChatResponse,
    ChatResponseMessage,
    TokenUsageSchema,
)
from app.services.model_service import ModelService
from app.services.usage_service import UsageService

MAX_TITLE_LENGTH = 60
# How many previous messages are included in the provider's context window.
HISTORY_LIMIT = 20
DEFAULT_TEMPERATURE = 0.7
# Built-in fallback provider, used only when nothing is configured at all.
FALLBACK_MODEL = "mock"
# Sent to the provider on every request. Kept short on purpose: on CPU-only
# hardware response time is dominated by the number of generated tokens, so a
# concise instruction keeps the demo responsive. Not stored in the database —
# it is a provider-level instruction, not part of the conversation.
SYSTEM_PROMPT = (
    "You are a helpful assistant on the AI Agent Platform. "
    "Answer concisely and directly."
)

logger = get_logger(__name__)


class ChatService:
    """Conversation lifecycle + chat completion."""

    def __init__(self, db: AsyncSession, llm: LLMProvider | None = None) -> None:
        self.db = db
        # The provider comes from the factory (OLLAMA_BASE_URL etc. live there),
        # so this service never names a concrete provider.
        self.llm = llm or get_llm_provider()
        self.usage = UsageService(db)
        self.models = ModelService(db)

    async def list_conversations(
        self, user_id: UUID, offset: int, limit: int
    ) -> tuple[list[Conversation], int]:
        """One page of a user's conversations (most recent first)."""
        total = await self.db.scalar(
            select(func.count())
            .select_from(Conversation)
            .where(Conversation.user_id == user_id)
        )
        result = await self.db.execute(
            select(Conversation)
            .where(Conversation.user_id == user_id)
            .order_by(Conversation.updated_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all()), int(total or 0)

    async def get_conversation(self, user_id: UUID, conversation_id: UUID) -> Conversation:
        """Return one of the user's conversations (ownership enforced)."""
        return await self._get_owned_conversation(user_id, conversation_id)

    async def get_messages(
        self, user_id: UUID, conversation_id: UUID, offset: int, limit: int
    ) -> tuple[list[Message], int]:
        """One page of messages inside a conversation, oldest first."""
        await self._get_owned_conversation(user_id, conversation_id)

        total = await self.db.scalar(
            select(func.count())
            .select_from(Message)
            .where(Message.conversation_id == conversation_id)
        )
        result = await self.db.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all()), int(total or 0)

    async def delete_conversation(self, user_id: UUID, conversation_id: UUID) -> None:
        """Delete a conversation and (via cascade) all of its messages."""
        conversation = await self._get_owned_conversation(user_id, conversation_id)
        await self.db.delete(conversation)
        await self.db.commit()

    async def chat(self, user: User, request: ChatRequest) -> ChatResponse:
        """Run the complete synchronous chat flow for one message."""
        # 1. Resolve or create the conversation.
        if request.conversation_id is not None:
            conversation = await self._get_owned_conversation(
                user.id, request.conversation_id
            )
        else:
            conversation = Conversation(
                user_id=user.id, title=_title_from(request.message)
            )
            self.db.add(conversation)
            await self.db.flush()

        # 2. Enforce the monthly allowance before doing any work.
        allowance = await self.usage.get_or_create_allowance(user.id)
        if not allowance.is_allowed:
            raise UsageLimitExceededException(
                "Monthly usage allowance exceeded. Please contact an administrator."
            )

        # 3. Resolve and validate the model. The frontend cannot run an
        #    arbitrary model: the name must be an active catalog entry or the
        #    configured default.
        model_name = await self._resolve_model(request.model)
        model_config = await self.models.get_by_name(model_name)
        temperature = (
            model_config.temperature if model_config else DEFAULT_TEMPERATURE
        )
        max_tokens = model_config.max_tokens if model_config else None

        # 4. Persist the user's message before generating, so the history
        #    query below (and a later refresh) already includes it.
        user_message = Message(
            conversation_id=conversation.id,
            role=MessageRole.USER,
            content=request.message,
        )
        self.db.add(user_message)
        await self.db.flush()

        # 5. Build the message history and call the provider. The system
        #    instruction leads so the model answers concisely.
        history = await self._recent_history(conversation.id)
        messages = [
            ChatMessage(role=MessageRole.SYSTEM, content=SYSTEM_PROMPT), *history
        ]
        response = await self._generate(
            conversation.id, model_name, messages, temperature, max_tokens
        )
        # 6. Persist the assistant's reply.
        assistant_message = Message(
            conversation_id=conversation.id,
            role=MessageRole.ASSISTANT,
            content=response.content,
            model=response.model,
            prompt_tokens=response.prompt_tokens,
            completion_tokens=response.completion_tokens,
            total_tokens=response.total_tokens,
        )
        self.db.add(assistant_message)

        # 7. Account for usage.
        await self.usage.record_usage(
            allowance, response.prompt_tokens, response.completion_tokens
        )

        await self.db.commit()

        return ChatResponse(
            conversation_id=conversation.id,
            message=ChatResponseMessage(
                role=MessageRole.ASSISTANT, content=response.content
            ),
            model=response.model,
            usage=TokenUsageSchema(
                prompt_tokens=response.prompt_tokens,
                completion_tokens=response.completion_tokens,
                total_tokens=response.total_tokens,
            ),
        )

    async def _resolve_model(self, requested: str | None) -> str:
        """Pick the model for this request and confirm it is permitted."""
        model_name = (
            requested
            or await self.models.resolve_default()
            or settings.ollama_default_model
            or FALLBACK_MODEL
        )

        # Only active catalog models and the configured default may run. The
        # built-in fallback provider is always allowed — it contacts nothing.
        allowed = await self.models.active_names()
        if settings.ollama_default_model:
            allowed.add(settings.ollama_default_model)
        if model_name not in allowed and model_name != FALLBACK_MODEL:
            logger.warning("Rejected request for unavailable model: %s", model_name)
            raise ValidationException(
                "The selected model is not available.",
                code="MODEL_NOT_AVAILABLE",
                details={"model": model_name},
            )
        return model_name

    async def _generate(
        self,
        conversation_id: UUID,
        model_name: str,
        history: list[ChatMessage],
        temperature: float,
        max_tokens: int | None,
    ) -> LLMResponse:
        """Call the provider, translating provider failures into clean errors."""
        logger.info(
            "LLM request started provider=%s model=%s conversation=%s messages=%d",
            self.llm.name,
            model_name,
            conversation_id,
            len(history),
        )
        started = time.perf_counter()
        try:
            response = await self.llm.generate(
                history,
                model=model_name,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        except LLMModelNotFoundError as exc:
            # The catalog allowed it, but the provider does not have it.
            logger.error(
                "LLM model not found provider=%s model=%s conversation=%s: %s",
                self.llm.name,
                model_name,
                conversation_id,
                exc,
            )
            raise ValidationException(
                "The selected model is not available.",
                code="MODEL_NOT_AVAILABLE",
                details={"model": model_name},
            )
        except LLMProviderError as exc:
            # Everything else (unreachable, timeout, empty response, HTTP
            # error) becomes a single user-friendly message; the technical
            # detail stays in the server log.
            logger.error(
                "LLM request failed provider=%s model=%s conversation=%s: %s",
                self.llm.name,
                model_name,
                conversation_id,
                exc,
            )
            raise ServiceUnavailableException(
                "AI service is currently unavailable. Please try again.",
                code="SERVICE_UNAVAILABLE",
            )

        elapsed_ms = (time.perf_counter() - started) * 1000
        logger.info(
            "LLM response completed provider=%s model=%s conversation=%s "
            "duration_ms=%.0f tokens=%d",
            self.llm.name,
            response.model,
            conversation_id,
            elapsed_ms,
            response.total_tokens,
        )
        return response

    async def _recent_history(
        self, conversation_id: UUID, limit: int = HISTORY_LIMIT
    ) -> list[ChatMessage]:
        """Load the tail of the conversation for the provider's context."""
        result = await self.db.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.desc())
            .limit(limit)
        )
        messages = list(result.scalars().all())
        messages.reverse()
        return [
            ChatMessage(role=m.role, content=m.content) for m in messages
        ]

    async def _get_owned_conversation(
        self, user_id: UUID, conversation_id: UUID
    ) -> Conversation:
        """Return the conversation if it belongs to the user, else 404."""
        result = await self.db.execute(
            select(Conversation).where(
                Conversation.id == conversation_id,
                Conversation.user_id == user_id,
            )
        )
        conversation = result.scalar_one_or_none()
        if conversation is None:
            raise not_found("Conversation", conversation_id)
        return conversation


def _title_from(message: str) -> str:
    """Derive a conversation title from its first message."""
    title = " ".join(message.split())
    return title[:MAX_TITLE_LENGTH] if title else "New chat"
