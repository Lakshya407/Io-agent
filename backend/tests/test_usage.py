"""Usage allowance tests (spec §35: usage calculation, allowance,
limit exceeded, reset)."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.models.usage import UsageAllowance
from app.models.user import User
from tests.conftest import _create_user, _login, _unique_email


async def _allowance_for(db_session, user_id) -> UsageAllowance:
    result = await db_session.execute(
        select(UsageAllowance).where(UsageAllowance.user_id == user_id)
    )
    return result.scalar_one()


async def test_new_user_gets_default_allowance(client, user_headers):
    response = await client.get("/api/v1/usage", headers=user_headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["monthly_token_limit"] > 0
    assert body["monthly_request_limit"] > 0
    assert body["tokens_used"] == 0
    assert body["requests_used"] == 0
    assert body["tokens_remaining"] == body["monthly_token_limit"]
    assert body["is_allowed"] is True
    assert body["reset_at"] > datetime.now(UTC).isoformat()


async def test_usage_reflects_chat_activity(client, user_headers):
    await client.post("/api/v1/chat", headers=user_headers, json={"message": "Hello"})

    response = await client.get("/api/v1/usage", headers=user_headers)
    assert response.json()["requests_used"] == 1
    assert response.json()["tokens_used"] > 0


async def test_usage_history_aggregates_by_day(client, user_headers):
    await client.post("/api/v1/chat", headers=user_headers, json={"message": "Hello"})
    await client.post("/api/v1/chat", headers=user_headers, json={"message": "Hi"})

    response = await client.get("/api/v1/usage/history", headers=user_headers)
    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 1  # both messages fall on the same day
    assert items[0]["requests"] == 2
    assert items[0]["tokens"] > 0


async def test_usage_history_filters_by_model(client, db_session, admin_headers, user_headers):
    create = await client.post(
        "/api/v1/admin/models",
        headers=admin_headers,
        json={"name": f"hist-{datetime.now(UTC).strftime('%H%M%S')}",
              "provider": "custom", "model_identifier": "mock"},
    )
    model_name = create.json()["name"]

    await client.post(
        "/api/v1/chat", headers=user_headers, json={"message": "Hello", "model": model_name}
    )
    await client.post("/api/v1/chat", headers=user_headers, json={"message": "No model"})

    response = await client.get(
        f"/api/v1/usage/history?model={model_name}", headers=user_headers
    )
    assert response.status_code == 200
    assert sum(item["requests"] for item in response.json()["items"]) == 1


async def test_admin_update_allowance(client, db_session, admin_headers):
    user = await _create_user(db_session, email=_unique_email())
    response = await client.patch(
        f"/api/v1/admin/users/{user.id}/allowance",
        headers=admin_headers,
        json={"monthly_token_limit": 1000, "monthly_request_limit": 50},
    )
    assert response.status_code == 200, response.text
    assert response.json()["monthly_token_limit"] == 1000
    assert response.json()["monthly_request_limit"] == 50


async def test_allowance_limit_blocks_chat(client, db_session):
    email = _unique_email()
    user = await _create_user(db_session, email=email)
    headers = await _login(client, email, "test-password-123")

    # Materialize the (lazily created) allowance and exhaust the token quota.
    # The quota check runs before generation, so an exhausted allowance must
    # already be at its limit for the request to be rejected.
    await client.get("/api/v1/usage", headers=headers)
    allowance = await _allowance_for(db_session, user.id)
    allowance.monthly_token_limit = 100
    allowance.tokens_used = 100  # exactly at the limit -> not allowed
    await db_session.commit()

    response = await client.post(
        "/api/v1/chat", headers=headers, json={"message": "Hello"}
    )
    assert response.status_code == 429
    assert response.json()["error"]["code"] == "USAGE_LIMIT_EXCEEDED"


async def test_allowance_resets_after_period_ends(client, db_session):
    email = _unique_email()
    user = await _create_user(db_session, email=email)
    headers = await _login(client, email, "test-password-123")

    # Materialize the allowance, then rewind its period into the past.
    await client.get("/api/v1/usage", headers=headers)
    allowance = await _allowance_for(db_session, user.id)
    allowance.tokens_used = 999_999
    allowance.requests_used = 999
    allowance.reset_at = datetime.now(UTC) - timedelta(days=1)  # period over
    await db_session.commit()

    response = await client.get("/api/v1/usage", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["tokens_used"] == 0
    assert body["requests_used"] == 0
    assert body["is_allowed"] is True


async def test_admin_usage_lists_every_user(client, db_session, admin_headers):
    await _create_user(db_session, email=_unique_email())
    response = await client.get("/api/v1/admin/usage", headers=admin_headers)
    assert response.status_code == 200
    assert response.json()["total"] >= 2  # admin + created user
    row = response.json()["items"][0]
    assert {"email", "name", "role", "tokens_used", "tokens_remaining"} <= set(row)


async def test_admin_dashboard_aggregates(client, db_session, admin_headers):
    user = await _create_user(db_session, email=_unique_email())
    # Materialize the lazily-created allowance, then record some usage.
    allowance = UsageAllowance(
        user_id=user.id, tokens_used=500, requests_used=5, monthly_token_limit=1000,
        monthly_request_limit=100, reset_at=datetime.now(UTC) + timedelta(days=10),
    )
    db_session.add(allowance)
    await db_session.commit()

    response = await client.get("/api/v1/admin/dashboard", headers=admin_headers)
    assert response.status_code == 200
    stats = response.json()
    assert stats["total_users"] >= 2
    assert stats["total_tokens"] >= 500
    assert stats["total_requests"] >= 5
    assert set(stats) == {
        "total_users", "active_users", "total_requests",
        "total_tokens", "active_models", "active_tools",
    }


async def test_admin_audit_logs_recorded(client, admin_headers):
    await client.post(
        "/api/v1/admin/models",
        headers=admin_headers,
        json={"name": f"aud-{datetime.now(UTC).strftime('%H%M%S%f')}",
              "provider": "custom", "model_identifier": "mock"},
    )

    response = await client.get("/api/v1/admin/audit-logs", headers=admin_headers)
    assert response.status_code == 200
    assert response.json()["total"] >= 1
    actions = {item["action"] for item in response.json()["items"]}
    assert "MODEL_CREATED" in actions
    entry = next(
        item for item in response.json()["items"] if item["action"] == "MODEL_CREATED"
    )
    assert "metadata" in entry  # exposed as `metadata`, not `metadata_`
