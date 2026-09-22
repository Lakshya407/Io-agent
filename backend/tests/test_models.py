"""Model & tool configuration tests (spec §35: create, update,
enable/disable)."""

import uuid


async def test_admin_create_model(client, admin_headers):
    response = await client.post(
        "/api/v1/admin/models",
        headers=admin_headers,
        json={
            "name": f"test-model-{uuid.uuid4().hex[:6]}",
            "provider": "openai",
            "model_identifier": "gpt-4o",
            "model_type": "chat",
        },
    )
    assert response.status_code == 201, response.text
    assert response.json()["provider"] == "openai"
    assert response.json()["is_active"] is True


async def test_create_duplicate_model_conflicts(client, admin_headers):
    name = f"dup-model-{uuid.uuid4().hex[:6]}"
    payload = {"name": name, "provider": "custom", "model_identifier": "mock"}
    await client.post("/api/v1/admin/models", headers=admin_headers, json=payload)

    response = await client.post("/api/v1/admin/models", headers=admin_headers, json=payload)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "MODEL_NAME_TAKEN"


async def test_regular_user_can_list_active_models(client, admin_headers, user_headers):
    await client.post(
        "/api/v1/admin/models",
        headers=admin_headers,
        json={"name": f"m-{uuid.uuid4().hex[:6]}", "provider": "custom",
              "model_identifier": "mock"},
    )
    response = await client.get("/api/v1/models", headers=user_headers)
    assert response.status_code == 200
    assert all(item["is_active"] for item in response.json()["items"])


async def test_inactive_models_hidden_by_default(client, admin_headers, user_headers):
    create = await client.post(
        "/api/v1/admin/models",
        headers=admin_headers,
        json={"name": f"m-{uuid.uuid4().hex[:6]}", "provider": "custom",
              "model_identifier": "mock"},
    )
    model_id = create.json()["id"]
    await client.patch(
        f"/api/v1/admin/models/{model_id}/status",
        headers=admin_headers,
        json={"is_active": False},
    )

    default = await client.get("/api/v1/models", headers=user_headers)
    assert all(item["id"] != model_id for item in default.json()["items"])

    all_models = await client.get(
        "/api/v1/models?active_only=false", headers=user_headers
    )
    assert any(item["id"] == model_id for item in all_models.json()["items"])


async def test_admin_update_model(client, admin_headers):
    create = await client.post(
        "/api/v1/admin/models",
        headers=admin_headers,
        json={"name": f"m-{uuid.uuid4().hex[:6]}", "provider": "custom",
              "model_identifier": "mock"},
    )
    model_id = create.json()["id"]

    response = await client.put(
        f"/api/v1/admin/models/{model_id}",
        headers=admin_headers,
        json={"temperature": 0.1, "max_tokens": 8192},
    )
    assert response.status_code == 200, response.text
    assert response.json()["temperature"] == 0.1
    assert response.json()["max_tokens"] == 8192


async def test_admin_delete_model(client, admin_headers):
    create = await client.post(
        "/api/v1/admin/models",
        headers=admin_headers,
        json={"name": f"m-{uuid.uuid4().hex[:6]}", "provider": "custom",
              "model_identifier": "mock"},
    )
    model_id = create.json()["id"]

    response = await client.delete(
        f"/api/v1/admin/models/{model_id}", headers=admin_headers
    )
    assert response.status_code == 204
    assert (await client.get(f"/api/v1/models/{model_id}", headers=admin_headers)).status_code == 404


async def test_regular_user_cannot_create_models(client, user_headers):
    response = await client.post(
        "/api/v1/admin/models",
        headers=user_headers,
        json={"name": "forbidden", "provider": "custom", "model_identifier": "x"},
    )
    assert response.status_code == 403


async def test_admin_create_tool(client, admin_headers):
    response = await client.post(
        "/api/v1/admin/tools",
        headers=admin_headers,
        json={
            "name": f"tool-{uuid.uuid4().hex[:6]}",
            "description": "A test tool",
            "type": "utility",
            "configuration": {"timeout": 30},
        },
    )
    assert response.status_code == 201, response.text
    assert response.json()["configuration"] == {"timeout": 30}


async def test_admin_disable_tool(client, admin_headers, user_headers):
    create = await client.post(
        "/api/v1/admin/tools",
        headers=admin_headers,
        json={"name": f"tool-{uuid.uuid4().hex[:6]}", "description": "d", "type": "search"},
    )
    tool_id = create.json()["id"]

    response = await client.patch(
        f"/api/v1/admin/tools/{tool_id}/status",
        headers=admin_headers,
        json={"is_active": False},
    )
    assert response.status_code == 200
    assert response.json()["is_active"] is False

    listed = await client.get("/api/v1/tools", headers=user_headers)
    assert all(item["id"] != tool_id for item in listed.json()["items"])
