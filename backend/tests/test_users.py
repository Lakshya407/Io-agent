"""User API tests (spec §35: create, read, update, delete, pagination)."""

import uuid

from tests.conftest import _create_user, _unique_email


async def test_get_me(client, user_headers):
    response = await client.get("/api/v1/users/me", headers=user_headers)
    assert response.status_code == 200
    assert response.json()["role"] == "user"


async def test_update_my_name(client, user_headers):
    response = await client.put(
        "/api/v1/users/me", headers=user_headers, json={"name": "Renamed"}
    )
    assert response.status_code == 200, response.text
    assert response.json()["name"] == "Renamed"


async def test_update_my_email_conflicts(client, db_session, user_headers):
    taken = _unique_email()
    await _create_user(db_session, email=taken)
    response = await client.put(
        "/api/v1/users/me", headers=user_headers, json={"email": taken}
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "EMAIL_ALREADY_REGISTERED"


async def test_admin_list_users_pagination(client, db_session, admin_headers):
    for _ in range(5):
        await _create_user(db_session, email=_unique_email())

    response = await client.get(
        "/api/v1/admin/users?page=1&page_size=3", headers=admin_headers
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) == 3
    assert body["total"] >= 6  # 5 created + the admin itself
    assert body["page"] == 1 and body["page_size"] == 3

    response = await client.get(
        "/api/v1/admin/users?page=2&page_size=3", headers=admin_headers
    )
    assert response.json()["page"] == 2


async def test_page_size_capped_at_100(client, admin_headers):
    response = await client.get(
        "/api/v1/admin/users?page_size=500", headers=admin_headers
    )
    assert response.status_code == 422


async def test_regular_user_cannot_list_users(client, user_headers):
    response = await client.get("/api/v1/users", headers=user_headers)
    assert response.status_code == 403


async def test_admin_get_user_by_id(client, db_session, admin_headers):
    user = await _create_user(db_session, email=_unique_email())
    response = await client.get(f"/api/v1/users/{user.id}", headers=admin_headers)
    assert response.status_code == 200
    assert response.json()["email"] == user.email


async def test_admin_get_nonexistent_user_404(client, admin_headers):
    response = await client.get(
        f"/api/v1/users/{uuid.uuid4()}", headers=admin_headers
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


async def test_admin_update_user_role(client, db_session, admin_headers):
    user = await _create_user(db_session, email=_unique_email())
    response = await client.patch(
        f"/api/v1/users/{user.id}",
        headers=admin_headers,
        json={"role": "admin", "name": "Promoted"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["role"] == "admin"
    assert response.json()["name"] == "Promoted"


async def test_admin_delete_user(client, db_session, admin_headers):
    user = await _create_user(db_session, email=_unique_email())
    response = await client.delete(f"/api/v1/users/{user.id}", headers=admin_headers)
    assert response.status_code == 204

    response = await client.get(f"/api/v1/users/{user.id}", headers=admin_headers)
    assert response.status_code == 404
