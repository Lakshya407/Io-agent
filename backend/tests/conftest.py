"""Shared pytest fixtures.

Every test runs inside a database transaction that is rolled back at teardown
(a SAVEPOINT is used so service-level ``commit()`` calls succeed without
escaping the test), giving each test a pristine database without any
expensive schema rebuilds.
"""

import uuid
from collections.abc import AsyncIterator
from typing import Any

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db
from app.core.rate_limit import rate_limit
from app.core.security import hash_password
from app.database.connection import engine
from app.llm.base import LLMProvider
from app.llm.mock import MockLLMProvider
from app.main import app
from app.models import UserRole
from app.models.user import User


@pytest.fixture
def llm_provider() -> LLMProvider:
    """The provider ChatService uses during tests.

    Never a live one: the suite must not depend on a locally running Ollama.
    Modules that need to observe provider calls can override this fixture with
    a recording provider.
    """
    return MockLLMProvider()


@pytest.fixture(autouse=True)
def _isolate_llm_provider(
    monkeypatch: pytest.MonkeyPatch, llm_provider: LLMProvider
) -> None:
    """Point ChatService at the test provider for every test.

    Without this, the chat API would instantiate the real (Ollama) provider
    and try to reach the network on every request.
    """
    monkeypatch.setattr(
        "app.services.chat_service.get_llm_provider",
        lambda *args: llm_provider,
    )


@pytest_asyncio.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    """A session bound to a transaction that is rolled back after the test.

    Uses a SAVEPOINT (restarted after every service-level ``commit()`` via the
    ``after_transaction_end`` listener) so the app's normal commit flow works
    while no change ever escapes the test.
    """
    async with engine.connect() as connection:
        transaction = await connection.begin()
        session = AsyncSession(
            bind=connection, expire_on_commit=False, autoflush=False
        )

        @event.listens_for(session.sync_session, "after_transaction_end")
        def _restart_savepoint(
            sync_session: Any, dbapi_transaction: Any
        ) -> None:
            # When the session commits its savepoint, open a fresh one so the
            # outer transaction is never actually committed.
            if dbapi_transaction.nested and not dbapi_transaction._parent.nested:
                sync_session.begin_nested()

        await session.begin_nested()
        try:
            yield session
        finally:
            await session.close()
            await transaction.rollback()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncIterator[AsyncClient]:
    """An async HTTP client talking to the app with overridden dependencies."""

    async def _override_db() -> AsyncIterator[AsyncSession]:
        yield db_session

    async def _no_rate_limit() -> None:
        return None

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[rate_limit] = _no_rate_limit
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
    finally:
        app.dependency_overrides.clear()


async def _create_user(
    db_session: AsyncSession,
    *,
    email: str,
    password: str = "test-password-123",
    name: str = "Test User",
    role: UserRole = UserRole.USER,
) -> User:
    """Insert a user directly (bypassing the API) for test setup."""
    user = User(
        email=email,
        password_hash=hash_password(password),
        name=name,
        role=role,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


async def _login(client: AsyncClient, email: str, password: str) -> dict[str, str]:
    """Log in and return the Authorization headers."""
    response = await client.post(
        "/api/v1/auth/login", data={"username": email, "password": password}
    )
    assert response.status_code == 200, response.text
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _unique_email() -> str:
    return f"test_{uuid.uuid4().hex[:8]}@example.com"


@pytest_asyncio.fixture
async def user_headers(client: AsyncClient, db_session: AsyncSession) -> dict[str, str]:
    """Auth headers for a freshly created standard user."""
    email = _unique_email()
    await _create_user(db_session, email=email)
    return await _login(client, email, "test-password-123")


@pytest_asyncio.fixture
async def admin_headers(
    client: AsyncClient, db_session: AsyncSession
) -> dict[str, str]:
    """Auth headers for a freshly created administrator."""
    email = _unique_email()
    await _create_user(
        db_session, email=email, name="Test Admin", role=UserRole.ADMIN
    )
    return await _login(client, email, "test-password-123")


__all__: list[Any] = ["client", "db_session", "user_headers", "admin_headers"]
