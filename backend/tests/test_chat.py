"""Chat API tests (spec §35: create conversation, send message, retrieve
messages, usage recording)."""

import uuid

from sqlalchemy import select

from app.models.conversation import Conversation
from app.models.usage import UsageAllowance
from tests.conftest import _unique_email


async def test_chat_creates_conversation_and_replies(client, user_headers):
    response = await client.post(
        "/api/v1/chat", headers=user_headers, json={"message": "Hello"}
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["conversation_id"]
    assert body["message"]["role"] == "assistant"
    assert body["message"]["content"]
    assert body["usage"]["total_tokens"] > 0


async def test_chat_reuses_existing_conversation(client, user_headers):
    first = await client.post(
        "/api/v1/chat", headers=user_headers, json={"message": "Hello"}
    )
    conversation_id = first.json()["conversation_id"]

    second = await client.post(
        "/api/v1/chat",
        headers=user_headers,
        json={"message": "Second message", "conversation_id": conversation_id},
    )
    assert second.status_code == 200
    assert second.json()["conversation_id"] == conversation_id


async def test_chat_unknown_conversation_404(client, user_headers):
    response = await client.post(
        "/api/v1/chat",
        headers=user_headers,
        json={"message": "Hi", "conversation_id": str(uuid.uuid4())},
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


async def test_list_conversations(client, user_headers):
    await client.post("/api/v1/chat", headers=user_headers, json={"message": "Hello"})
    await client.post("/api/v1/chat", headers=user_headers, json={"message": "Again"})

    response = await client.get("/api/v1/conversations", headers=user_headers)
    assert response.status_code == 200
    assert response.json()["total"] == 2


async def test_list_messages_returns_full_history(client, user_headers):
    create = await client.post(
        "/api/v1/chat", headers=user_headers, json={"message": "Hello"}
    )
    conversation_id = create.json()["conversation_id"]
    await client.post(
        "/api/v1/chat",
        headers=user_headers,
        json={"message": "Second", "conversation_id": conversation_id},
    )

    response = await client.get(
        f"/api/v1/conversations/{conversation_id}/messages", headers=user_headers
    )
    assert response.status_code == 200
    roles = [item["role"] for item in response.json()["items"]]
    assert roles == ["user", "assistant", "user", "assistant"]


async def test_delete_conversation(client, user_headers):
    create = await client.post(
        "/api/v1/chat", headers=user_headers, json={"message": "Hello"}
    )
    conversation_id = create.json()["conversation_id"]

    response = await client.delete(
        f"/api/v1/conversations/{conversation_id}", headers=user_headers
    )
    assert response.status_code == 204

    response = await client.get(
        f"/api/v1/conversations/{conversation_id}", headers=user_headers
    )
    assert response.status_code == 404


async def test_user_cannot_see_other_users_conversation(client, db_session, user_headers):
    # A real conversation owned by a different user.
    from tests.conftest import _create_user

    other_user = await _create_user(db_session, email=_unique_email())
    other = Conversation(user_id=other_user.id, title="Not yours")
    db_session.add(other)
    await db_session.commit()

    response = await client.get(
        f"/api/v1/conversations/{other.id}", headers=user_headers
    )
    assert response.status_code == 404


async def test_chat_records_usage(client, db_session, user_headers):
    await client.post("/api/v1/chat", headers=user_headers, json={"message": "Hello"})
    await client.post(
        "/api/v1/chat", headers=user_headers, json={"message": "Second message"}
    )

    response = await client.get("/api/v1/usage", headers=user_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["requests_used"] == 2
    assert body["tokens_used"] > 0
    assert body["is_allowed"] is True


async def test_chat_blocked_when_allowance_exhausted(client, db_session, user_headers):
    # The allowance is created lazily; materialize it first, then pin it to a
    # single remaining request. Filter by the current user — the shared
    # database contains rows from other runs.
    await client.get("/api/v1/usage", headers=user_headers)
    me = await client.get("/api/v1/users/me", headers=user_headers)
    user_id = me.json()["id"]
    allowance = (
        await db_session.execute(
            select(UsageAllowance).where(UsageAllowance.user_id == user_id)
        )
    ).scalar_one()
    allowance.monthly_request_limit = 1
    await db_session.commit()

    first = await client.post(
        "/api/v1/chat", headers=user_headers, json={"message": "Hello"}
    )
    assert first.status_code == 200

    second = await client.post(
        "/api/v1/chat", headers=user_headers, json={"message": "Again"}
    )
    assert second.status_code == 429
    assert second.json()["error"]["code"] == "USAGE_LIMIT_EXCEEDED"


async def test_chat_without_token_is_unauthorized(client):
    response = await client.post("/api/v1/chat", json={"message": "Hello"})
    assert response.status_code == 401


async def test_empty_message_rejected(client, user_headers):
    response = await client.post(
        "/api/v1/chat", headers=user_headers, json={"message": ""}
    )
    assert response.status_code == 422
