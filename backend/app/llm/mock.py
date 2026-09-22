"""Mock LLM provider.

The first working version of the chat flow uses this deterministic, dependency
free provider. It validates the whole request/response path (auth → usage
check → chat service → storage → accounting) before any real provider is
introduced, and never calls the network.
"""

from app.llm.base import LLMProvider, LLMResponse, LLMStreamChunk
from app.schemas.chat import ChatMessage

_GREETINGS = ("hello", "hi", "hey", "greetings", "yo")
_BANNER = "Hello! This is the AI Agent Platform backend."


def _estimate_tokens(text: str) -> int:
    """Rough token estimate (~4 characters per token, at least one)."""
    return max(1, len(text) // 4)


class MockLLMProvider(LLMProvider):
    """Echo-style stand-in for a real LLM backend."""

    name = "mock"

    async def generate(
        self,
        messages: list[ChatMessage],
        *,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        **kwargs: object,
    ) -> LLMResponse:
        prompt_text = " ".join(m.content for m in messages).strip()
        last_user = next(
            (m.content.strip() for m in reversed(messages) if m.role == "user"),
            "",
        )

        normalized = last_user.lower().rstrip("!?., ")
        if normalized in _GREETINGS or any(
            normalized.startswith(g) for g in _GREETINGS
        ):
            content = _BANNER
        else:
            content = f"You said: {last_user}"

        prompt_tokens = _estimate_tokens(prompt_text)
        completion_tokens = _estimate_tokens(content)
        return LLMResponse(
            content=content,
            model=model or self.name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            metadata={"provider": self.name},
        )

    async def stream(
        self,
        messages: list[ChatMessage],
        *,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        **kwargs: object,
    ):
        """Yield the deterministic reply word-by-word, then a done chunk."""
        response = await self.generate(
            messages, model=model, temperature=temperature,
            max_tokens=max_tokens, **kwargs,
        )
        words = response.content.split(" ")
        for i, word in enumerate(words):
            piece = word if i == len(words) - 1 else word + " "
            yield LLMStreamChunk(
                content=piece, done=False, model=response.model,
                metadata={"provider": self.name},
            )
        yield LLMStreamChunk(
            content="", done=True, model=response.model,
            prompt_tokens=response.prompt_tokens,
            completion_tokens=response.completion_tokens,
            total_tokens=response.total_tokens,
            metadata={"provider": self.name},
        )
