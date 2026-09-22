"""Abstract LLM provider interface.

The chat service depends only on this interface so concrete providers
(OpenAI, Anthropic, Ollama, custom) can be added later without changing the
API or service layers. Provider failures are raised as ``LLMProviderError``
subclasses so the service layer can translate them into clean HTTP errors
without leaking provider internals.
"""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass, field

from app.schemas.chat import ChatMessage


@dataclass
class LLMResponse:
    """Normalized result of a non-streaming generation."""

    content: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass
class LLMStreamChunk:
    """One normalized chunk of a streaming generation."""

    content: str
    done: bool = False
    model: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    metadata: dict[str, object] = field(default_factory=dict)


class LLMProviderError(Exception):
    """Base class for every LLM provider failure.

    The service layer catches these and maps them to user-friendly HTTP
    errors; the original technical detail is logged server-side only.
    """


class LLMUnavailableError(LLMProviderError):
    """The provider endpoint could not be reached (e.g. Ollama is not running)."""


class LLMTimeoutError(LLMProviderError):
    """The provider did not answer within the configured timeout."""


class LLMModelNotFoundError(LLMProviderError):
    """The requested model is not available on the provider."""


class LLMEmptyResponseError(LLMProviderError):
    """The provider returned an empty completion."""


class LLMProvider(ABC):
    """Every LLM backend implements this contract."""

    name: str = "base"

    @abstractmethod
    async def generate(
        self,
        messages: list[ChatMessage],
        *,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        **kwargs: object,
    ) -> LLMResponse:
        """Generate a completion for the given message history."""
        raise NotImplementedError

    async def stream(
        self,
        messages: list[ChatMessage],
        *,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        **kwargs: object,
    ) -> AsyncIterator[LLMStreamChunk]:
        """Stream a completion as normalized chunks.

        Yields ``LLMStreamChunk`` items as they arrive; the final chunk has
        ``done=True`` with token accounting when the provider reports it.
        """
        raise NotImplementedError
        yield LLMStreamChunk(content="")  # pragma: no cover

    async def generate_stream(
        self, messages: list[ChatMessage], **kwargs: object
    ) -> AsyncIterator[str]:
        """Legacy string-chunk stream (kept for compatibility).

        Delegates to :meth:`stream` and yields raw content strings.
        """
        async for chunk in self.stream(messages, **kwargs):
            if chunk.content:
                yield chunk.content
