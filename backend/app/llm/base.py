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

    async def generate_stream(
        self, messages: list[ChatMessage], **kwargs: object
    ) -> AsyncIterator[str]:
        """Stream a completion as token chunks (SSE-ready placeholder).

        Not implemented yet — the request/response version comes first.
        """
        raise NotImplementedError
        # ``yield`` makes this an async generator for type-checkers.
        yield ""  # pragma: no cover
