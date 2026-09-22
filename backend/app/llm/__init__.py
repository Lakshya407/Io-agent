"""LLM provider package.

Providers implement ``LLMProvider``; the chat service obtains one through
``get_llm_provider`` so it stays decoupled from any specific backend.
"""

from app.llm.base import (
    LLMEmptyResponseError,
    LLMModelNotFoundError,
    LLMProvider,
    LLMProviderError,
    LLMResponse,
    LLMTimeoutError,
    LLMUnavailableError,
)
from app.llm.factory import get_llm_provider
from app.llm.mock import MockLLMProvider
from app.llm.ollama import OllamaProvider

__all__ = [
    "LLMEmptyResponseError",
    "LLMModelNotFoundError",
    "LLMProvider",
    "LLMProviderError",
    "LLMResponse",
    "LLMTimeoutError",
    "LLMUnavailableError",
    "MockLLMProvider",
    "OllamaProvider",
    "get_llm_provider",
]
