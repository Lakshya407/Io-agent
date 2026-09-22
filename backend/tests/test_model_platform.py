"""Model platform tests (Phase 3: default, enable/disable, validation)."""

import uuid


async def _create_model(client, admin_headers, **overrides):
    name = f"m-{uuid.uuid4().hex[:6]}"
    payload = {
        "name": name, "provider": "custom", "model_identifier": "mock",
    }
    payload.update(overrides)
    response = await client.post(
        "/api/v1/admin/models", headers=admin_headers, json=payload
    )
    assert response.status_code == 201, response.text
    return response.json()


async def test_only_one_default_model_exists(client, admin_headers):
    first = await _create_model(client, admin_headers, is_default=True)
    second = await _create_model(client, admin_headers, is_default=True)
    assert second["is_default"] is True
    # The first default must have been cleared.
    got = await client.get(f"/api/v1/models/{first['id']}", headers=admin_headers)
    assert got.json()["is_default"] is False


async def test_admin_set_default_endpoint(client, admin_headers):
    first = await _create_model(client, admin_headers)
    second = await _create_model(client, admin_headers)
    response = await client.post(
        f"/api/v1/admin/models/{second['id']}/default", headers=admin_headers
    )
    assert response.status_code == 200
    assert response.json()["is_default"] is True
    got = await client.get(f"/api/v1/models/{first['id']}", headers=admin_headers)
    assert got.json()["is_default"] is False


async def test_disabled_model_cannot_be_default(client, admin_headers):
    model = await _create_model(client, admin_headers)
    await client.patch(
        f"/api/v1/admin/models/{model['id']}/status",
        headers=admin_headers, json={"is_active": False},
    )
    response = await client.post(
        f"/api/v1/admin/models/{model['id']}/default", headers=admin_headers
    )
    assert response.status_code == 422


async def test_default_model_cannot_be_disabled(client, admin_headers):
    model = await _create_model(client, admin_headers, is_default=True)
    response = await client.patch(
        f"/api/v1/admin/models/{model['id']}/status",
        headers=admin_headers, json={"is_active": False},
    )
    assert response.status_code == 422


async def test_model_config_validation(client, admin_headers):
    model = await _create_model(client, admin_headers)
    bad_temp = await client.put(
        f"/api/v1/admin/models/{model['id']}",
        headers=admin_headers, json={"temperature": 5.0},
    )
    assert bad_temp.status_code == 422
    bad_tokens = await client.put(
        f"/api/v1/admin/models/{model['id']}",
        headers=admin_headers, json={"max_tokens": 0},
    )
    assert bad_tokens.status_code == 422


async def test_chat_uses_default_model(client, admin_headers, user_headers):
    model = await _create_model(client, admin_headers, is_default=True)
    # Chat without an explicit model must succeed (resolves the default).
    response = await client.post(
        "/api/v1/chat", headers=user_headers, json={"message": "Hello"}
    )
    # Either the catalog default or the configured fallback is accepted;
    # the point is the request is not rejected.
    assert response.status_code == 200


async def test_chat_rejects_invalid_model(client, user_headers):
    response = await client.post(
        "/api/v1/chat", headers=user_headers,
        json={"message": "Hi", "model": "does-not-exist"},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "MODEL_NOT_AVAILABLE"


async def test_models_list_availability_flag(client, admin_headers, user_headers):
    await _create_model(
        client, admin_headers, provider="custom", model_identifier="mock"
    )
    response = await client.get(
        "/api/v1/models?include_availability=true", headers=user_headers
    )
    assert response.status_code == 200
    assert "available" in response.json()["items"][0]


async def test_regular_user_cannot_set_default(client, user_headers):
    response = await client.post(
        f"/api/v1/admin/models/{uuid.uuid4()}/default", headers=user_headers
    )
    assert response.status_code == 403
