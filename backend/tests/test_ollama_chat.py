"""Chat flow tests against the real ChatService with a mocked provider.

These cover the LLM integration contract end to end: message persistence,
conversation history being passed to the provider, model allow-listing and the
translation of provider failures into clean HTTP errors. No live Ollama is
contacted — the provider is swapped out by the ``llm_provider`` fixture.
"""

import pytest
from sqlalchemy import select
from uuid import UUID

from app.llm.base import (
    LLMModelNotFoundError,
    LLMProvider,
    LLMResponse,
    LLMUnavailableError,
)
from app.models.conversation import Conversation
from app.models.message import Message
from app.schemas.chat import ChatMessage
from app.services.chat_service import SYSTEM_PROMPT
from tests.conftest import _create_user, _unique_email


class RecordingProvider(LLMProvider):
    """Provider that records every call so tests can assert on it."""

    name = "recording"

    def __init__(self, content: str = "Real LLM reply.", error: BaseException | None = None) -> None:
        self.content = content
        self.error = error
        self.calls: list[dict[str, object]] = []

    async def generate(
        self,
        messages: list[ChatMessage],
        *,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        **kwargs: object,
    ) -> LLMResponse:
        self.calls.append(
            {
                "messages": list(messages),
                "model": model,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
        )
        if self.error is not None:
            raise self.error
        return LLMResponse(
            content=self.content,
            model=model or self.name,
            prompt_tokens=10,
            completion_tokens=20,
            total_tokens=30,
            metadata={"provider": self.name},
        )


@pytest.fixture
def llm_provider() -> RecordingProvider:
    """Override the suite-wide provider so chat calls are observable."""
    return RecordingProvider()


async def test_chat_persists_user_and_assistant_messages(
    client, user_headers, llm_provider
):
    response = await client.post(
        "/api/v1/chat", headers=user_headers, json={"message": "Explain Docker"}
    )
    assert response.status_code == 200, response.text
    conversation_id = response.json()["conversation_id"]

    messages = await client.get(
        f"/api/v1/conversations/{conversation_id}/messages", headers=user_headers
    )
    roles = [item["role"] for item in messages.json()["items"]]
    assert roles == ["user", "assistant"]
    contents = {item["role"]: item["content"] for item in messages.json()["items"]}
    assert contents["user"] == "Explain Docker"
    assert contents["assistant"] == "Real LLM reply."


async def test_chat_passes_full_history_to_provider(client, user_headers, llm_provider):
    first = await client.post(
        "/api/v1/chat", headers=user_headers, json={"message": "What is Docker?"}
    )
    conversation_id = first.json()["conversation_id"]
    await client.post(
        "/api/v1/chat",
        headers=user_headers,
        json={"message": "How is it different from a VM?", "conversation_id": conversation_id},
    )

    assert len(llm_provider.calls) == 2
    first_call = llm_provider.calls[0]["messages"]
    second_call = llm_provider.calls[1]["messages"]

    assert len(first_call) == 2
    assert first_call[0].role == "system"
    assert first_call[1].role == "user"
    assert first_call[1].content == "What is Docker?"

    # The second request must include the system instruction, the previous
    # exchange plus the new turn. Exact tail ordering is not asserted here on
    # purpose: every message in a test shares one outer transaction, and
    # PostgreSQL's now() is the *transaction* start time, so all rows tie on
    # created_at. Real requests each run in their own transaction, where the
    # timestamps (and thus the ordering) differ.
    assert [m.role for m in second_call] == ["system", "user", "assistant", "user"]
    contents = {m.content for m in second_call}
    assert contents == {
        SYSTEM_PROMPT,
        "What is Docker?",
        "Real LLM reply.",
        "How is it different from a VM?",
    }


async def test_chat_uses_configured_default_model(client, user_headers, llm_provider):
    response = await client.post(
        "/api/v1/chat", headers=user_headers, json={"message": "Hello"}
    )
    assert response.status_code == 200
    assert response.json()["model"] == llm_provider.calls[0]["model"]


async def test_chat_rejects_model_not_in_catalog(client, user_headers, llm_provider):
    response = await client.post(
        "/api/v1/chat",
        headers=user_headers,
        json={"message": "Hello", "model": "gpt-4o"},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "MODEL_NOT_AVAILABLE"
    # The provider must never have been called for a disallowed model.
    assert llm_provider.calls == []


async def test_chat_translates_provider_model_error(client, user_headers, llm_provider):
    llm_provider.error = LLMModelNotFoundError("model not found")

    response = await client.post(
        "/api/v1/chat", headers=user_headers, json={"message": "Hello"}
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "MODEL_NOT_AVAILABLE"


async def test_chat_translates_provider_outage(client, user_headers, db_session, llm_provider):
    llm_provider.error = LLMUnavailableError("connection refused")

    # A known conversation so the persisted rows can be inspected precisely.
    me = await client.get("/api/v1/users/me", headers=user_headers)
    conversation = Conversation(
        user_id=UUID(me.json()["id"]), title="Outage test"
    )
    db_session.add(conversation)
    await db_session.commit()

    response = await client.post(
        "/api/v1/chat",
        headers=user_headers,
        json={"message": "Hello", "conversation_id": str(conversation.id)},
    )
    # Clean, user-facing error instead of a 500/stack trace.
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "SERVICE_UNAVAILABLE"
    assert response.json()["error"]["message"] == (
        "AI service is currently unavailable. Please try again."
    )

    # No assistant reply is ever written when the provider fails.
    rows = (
        await db_session.execute(
            select(Message).where(Message.conversation_id == conversation.id)
        )
    ).scalars().all()
    assert all(row.role != "assistant" for row in rows)


async def test_chat_persists_across_conversations(client, user_headers, llm_provider):
    first = await client.post(
        "/api/v1/chat", headers=user_headers, json={"message": "Topic A"}
    )
    second = await client.post(
        "/api/v1/chat", headers=user_headers, json={"message": "Topic B"}
    )
    assert first.json()["conversation_id"] != second.json()["conversation_id"]

    # The two conversations must not share history (the system instruction is
    # always present, so each call has exactly one user turn).
    assert len(llm_provider.calls) == 2
    assert [m.role for m in llm_provider.calls[1]["messages"]] == [
        "system",
        "user",
    ]


async def test_chat_cannot_use_other_users_conversation(
    client, db_session, user_headers, llm_provider
):
    other_user = await _create_user(db_session, email=_unique_email())
    other = Conversation(user_id=other_user.id, title="Not yours")
    db_session.add(other)
    await db_session.commit()

    response = await client.post(
        "/api/v1/chat",
        headers=user_headers,
        json={"message": "Hello", "conversation_id": str(other.id)},
    )
    assert response.status_code == 404
    assert llm_provider.calls == []


async def test_chat_requires_authentication(client):
    response = await client.post("/api/v1/chat", json={"message": "Hello"})
    assert response.status_code == 401


async def test_usage_recorded_from_provider_tokens(client, user_headers, llm_provider):
    await client.post("/api/v1/chat", headers=user_headers, json={"message": "Hello"})

    usage = await client.get("/api/v1/usage", headers=user_headers)
    assert usage.status_code == 200
    assert usage.json()["tokens_used"] == 30  # 10 prompt + 20 completion
    assert usage.json()["requests_used"] == 1
