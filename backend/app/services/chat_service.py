"""Chat service: conversation management and message completion.

Implements the flow required by ``POST /api/v1/chat``:

    authentication → usage check → create/reuse conversation → resolve model
    → persist user message → LLM provider (Ollama by default) → persist reply
    → record usage → response

Conversation history is loaded from PostgreSQL and passed to the provider on
every request, so follow-up questions keep their context.
"""

import asyncio
import time
from collections.abc import AsyncIterator
from typing import Any
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
# The model name is interpolated per request: small local models otherwise
# fall back to their training-data prior and claim to be GPT-4/ChatGPT when
# asked "which model are you".
SYSTEM_PROMPT_TEMPLATE = (
    "You are AI Agent, powered by the {model} model running locally via Ollama. "
    "Answer concisely and directly. "
    "If asked which model you are, name {model} exactly — "
    "never claim to be GPT-4, ChatGPT, or any other OpenAI model."
)


def system_prompt_for(model_name: str) -> str:
    """Render the per-request system instruction for the resolved model."""
    return SYSTEM_PROMPT_TEMPLATE.format(model=model_name)

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
        #    instruction leads so the model answers concisely and states its
        #    real identity instead of hallucinating a vendor model.
        history = await self._recent_history(conversation.id)
        messages = [
            ChatMessage(role=MessageRole.SYSTEM, content=system_prompt_for(model_name)),
            *history,
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

    async def stream_chat(
        self, user: User, request: ChatRequest
    ) -> AsyncIterator[dict[str, Any]]:
        """Yield SSE-ready events for one streaming chat turn.

        Event sequence on success::

            activity (started) → activity (model) → message_start →
            token* → activity (generating) → message_complete

        On failure a single ``error`` event is yielded instead of
        ``message_complete``. The caller (API layer) formats these dicts as
        ``event: <type>\\ndata: <json>`` frames.

        Persistence: exactly ONE assistant row is created (empty placeholder),
        tokens are accumulated in memory, and the row is updated once on
        completion. Client aborts surface as ``asyncio.CancelledError`` in the
        API layer — the ``finally``-style handling here still persists the
        partial content with ``status="stopped"`` before re-raising.
        """
        # 1. Resolve or create the conversation (ownership enforced).
        if request.conversation_id is not None:
            conversation = await self._get_owned_conversation(
                user.id, request.conversation_id
            )
            is_new = False
        else:
            conversation = Conversation(
                user_id=user.id, title=_title_from(request.message)
            )
            self.db.add(conversation)
            await self.db.flush()
            is_new = True

        # 2. Allowance check before any work.
        allowance = await self.usage.get_or_create_allowance(user.id)
        if not allowance.is_allowed:
            yield {
                "event": "error",
                "data": {
                    "code": "USAGE_LIMIT_EXCEEDED",
                    "message": (
                        "Monthly usage allowance exceeded. "
                        "Please contact an administrator."
                    ),
                },
            }
            return

        # 3. Resolve + validate the model.
        try:
            model_name = await self._resolve_model(request.model)
        except ValidationException as exc:
            yield {
                "event": "error",
                "data": {"code": exc.code, "message": exc.message},
            }
            return
        model_config = await self.models.get_by_name(model_name)
        temperature = (
            model_config.temperature if model_config else DEFAULT_TEMPERATURE
        )
        max_tokens = model_config.max_tokens if model_config else None

        # 4. Persist the user message first.
        self.db.add(
            Message(
                conversation_id=conversation.id,
                role=MessageRole.USER,
                content=request.message,
            )
        )
        await self.db.flush()

        # 5. Create the single assistant placeholder row.
        assistant_message = Message(
            conversation_id=conversation.id,
            role=MessageRole.ASSISTANT,
            content="",
            model=model_name,
            status="completed",
        )
        self.db.add(assistant_message)
        await self.db.flush()
        await self.db.commit()

        yield {
            "event": "activity",
            "data": {"stage": "started", "detail": "Request received"},
        }
        yield {
            "event": "activity",
            "data": {
                "stage": "model",
                "detail": f"Using {model_name}",
                "model": model_name,
                "provider": self.llm.name,
            },
        }
        yield {
            "event": "message_start",
            "data": {
                "message_id": str(assistant_message.id),
                "conversation_id": str(conversation.id),
                "model": model_name,
                "is_new_conversation": is_new,
            },
        }
        yield {
            "event": "activity",
            "data": {"stage": "generating", "detail": "Generating response"},
        }

        history = await self._recent_history(conversation.id)
        messages = [
            ChatMessage(
                role=MessageRole.SYSTEM, content=system_prompt_for(model_name)
            ),
            *history,
        ]

        logger.info(
            "LLM stream started provider=%s model=%s conversation=%s messages=%d",
            self.llm.name, model_name, conversation.id, len(messages),
        )
        started = time.perf_counter()
        accumulated: list[str] = []
        prompt_tokens = 0
        completion_tokens = 0
        response_model = model_name
        stopped = False
        try:
            async for chunk in self.llm.stream(
                messages, model=model_name,
                temperature=temperature, max_tokens=max_tokens,
            ):
                if chunk.content:
                    accumulated.append(chunk.content)
                    yield {
                        "event": "token",
                        "data": {"content": chunk.content},
                    }
                if chunk.done:
                    prompt_tokens = chunk.prompt_tokens
                    completion_tokens = chunk.completion_tokens
                    if chunk.model:
                        response_model = chunk.model
            final_content = "".join(accumulated).strip()
            if not final_content:
                final_content = ""
            assistant_message.content = final_content
            assistant_message.model = response_model
            assistant_message.prompt_tokens = prompt_tokens
            assistant_message.completion_tokens = completion_tokens
            assistant_message.total_tokens = prompt_tokens + completion_tokens
            assistant_message.status = "completed"
            await self.usage.record_usage(
                allowance, prompt_tokens, completion_tokens
            )
            await self.db.commit()
            elapsed_ms = (time.perf_counter() - started) * 1000
            logger.info(
                "LLM stream completed provider=%s model=%s conversation=%s "
                "duration_ms=%.0f tokens=%d",
                self.llm.name, response_model, conversation.id,
                elapsed_ms, prompt_tokens + completion_tokens,
            )
            yield {
                "event": "activity",
                "data": {
                    "stage": "completed", "detail": "Response generated",
                    "duration_ms": round(elapsed_ms),
                },
            }
            yield {
                "event": "message_complete",
                "data": {
                    "message_id": str(assistant_message.id),
                    "conversation_id": str(conversation.id),
                    "model": response_model,
                    "status": "completed",
                    "usage": {
                        "prompt_tokens": prompt_tokens,
                        "completion_tokens": completion_tokens,
                        "total_tokens": prompt_tokens + completion_tokens,
                    },
                },
            }
        except (asyncio.CancelledError, GeneratorExit):
            stopped = True
            raise
        except LLMModelNotFoundError as exc:
            logger.error(
                "LLM stream model not found provider=%s model=%s: %s",
                self.llm.name, model_name, exc,
            )
            assistant_message.content = "".join(accumulated)
            assistant_message.status = "error"
            await self.db.commit()
            yield {
                "event": "error",
                "data": {
                    "code": "MODEL_NOT_AVAILABLE",
                    "message": "The selected model is not available.",
                },
            }
        except LLMProviderError as exc:
            logger.error(
                "LLM stream failed provider=%s model=%s conversation=%s: %s",
                self.llm.name, model_name, conversation.id, exc,
            )
            partial = "".join(accumulated)
            if partial.strip():
                # Keep what was already generated so a refresh shows it.
                assistant_message.content = partial
                assistant_message.status = "error"
                await self.db.commit()
            else:
                await self.db.delete(assistant_message)
                await self.db.commit()
            # Map to user-friendly messages without leaking internals.
            msg = "AI service is currently unavailable. Please try again."
            if isinstance(exc, LLMModelNotFoundError):
                msg = "The selected model is not available."
            yield {"event": "error", "data": {"message": msg}}
        finally:
            if stopped:
                try:
                    partial = "".join(accumulated)
                    assistant_message.content = partial
                    assistant_message.status = "stopped"
                    await self.db.commit()
                except Exception:
                    logger.exception("Failed to persist stopped stream")

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
        # Skip empty rows (e.g. a streaming placeholder committed before
        # generation starts) — the provider schema requires non-empty content.
        return [
            ChatMessage(role=m.role, content=m.content)
            for m in messages
            if m.content and m.content.strip()
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
