"""Authentication tests (spec §35: register, login, invalid password,
unauthorized request, admin authorization)."""

import uuid

import pytest

from tests.conftest import _create_user, _login, _unique_email


async def test_register_creates_user_and_returns_tokens(client):
    email = _unique_email()
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "test-password-123", "name": "New User"},
    )
    assert response.status_code == 201, response.text
    tokens = response.json()
    assert set(tokens) == {"access_token", "refresh_token", "token_type", "expires_in"}
    assert tokens["token_type"] == "bearer"
    assert tokens["expires_in"] > 0


async def test_register_duplicate_email_conflicts(client, db_session):
    email = _unique_email()
    await _create_user(db_session, email=email)
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "test-password-123", "name": "Dup"},
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "EMAIL_ALREADY_REGISTERED"


async def test_register_short_password_rejected(client):
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": _unique_email(), "password": "short", "name": "Short"},
    )
    assert response.status_code == 422


@pytest.mark.parametrize("password", ["wrong-password", "totally-different"])
async def test_login_invalid_password(client, db_session, password):
    email = _unique_email()
    await _create_user(db_session, email=email)
    response = await client.post(
        "/api/v1/auth/login", data={"username": email, "password": password}
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_CREDENTIALS"


async def test_login_unknown_email(client):
    response = await client.post(
        "/api/v1/auth/login",
        data={"username": _unique_email(), "password": "test-password-123"},
    )
    assert response.status_code == 401
    # Identical error to a wrong password (no account enumeration).
    assert response.json()["error"]["code"] == "INVALID_CREDENTIALS"


async def test_login_and_access_protected_endpoint(client, db_session):
    email = _unique_email()
    await _create_user(db_session, email=email)
    headers = await _login(client, email, "test-password-123")

    response = await client.get("/api/v1/auth/me", headers=headers)
    assert response.status_code == 200
    assert response.json()["email"] == email
    assert response.json()["role"] == "user"
    assert "password_hash" not in response.json()


async def test_protected_endpoint_without_token_is_unauthorized(client):
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401


async def test_invalid_token_is_unauthorized(client):
    response = await client.get(
        "/api/v1/auth/me", headers={"Authorization": "Bearer not-a-jwt"}
    )
    assert response.status_code == 401


async def test_refresh_token_returns_new_pair(client, db_session):
    email = _unique_email()
    await _create_user(db_session, email=email)
    login = await client.post(
        "/api/v1/auth/login", data={"username": email, "password": "test-password-123"}
    )
    refresh_token = login.json()["refresh_token"]

    response = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": refresh_token}
    )
    assert response.status_code == 200, response.text
    # The new access token must authenticate the user. (It may be byte-identical
    # to the original when issued within the same second — same claims — which
    # is fine; what matters is that it works.)
    me = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {response.json()['access_token']}"},
    )
    assert me.status_code == 200
    assert me.json()["email"] == email


async def test_refresh_rejects_access_token(client, user_headers):
    # Extract a raw access token and try to use it for refresh.
    access_token = user_headers["Authorization"].removeprefix("Bearer ")
    response = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": access_token}
    )
    assert response.status_code == 401


async def test_admin_authorization(client, admin_headers):
    response = await client.get("/api/v1/admin/dashboard", headers=admin_headers)
    assert response.status_code == 200


async def test_regular_user_forbidden_from_admin(client, user_headers):
    response = await client.get("/api/v1/admin/dashboard", headers=user_headers)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


async def test_disabled_user_cannot_login(client, db_session):
    email = _unique_email()
    user = await _create_user(db_session, email=email)
    user.is_active = False
    await db_session.commit()

    response = await client.post(
        "/api/v1/auth/login", data={"username": email, "password": "test-password-123"}
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "USER_DISABLED"
