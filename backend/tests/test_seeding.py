"""Startup seeding tests for the Ollama model catalog."""

from contextlib import asynccontextmanager
import uuid

import pytest
from sqlalchemy import select, update

from app.core.config import settings
from app.main import _configured_model_names, seed_default_model
from app.models.model import ModelConfig


def test_configured_model_names_parses_list(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "ollama_default_model", "llama3.2:1b")
    monkeypatch.setattr(settings, "ollama_models", " qwen2.5:0.5b , ,phi3:mini ")

    assert _configured_model_names() == {
        "llama3.2:1b",
        "qwen2.5:0.5b",
        "phi3:mini",
    }


def test_configured_model_names_without_extras(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "ollama_default_model", "llama3.2:1b")
    monkeypatch.setattr(settings, "ollama_models", "")

    assert _configured_model_names() == {"llama3.2:1b"}


async def test_seed_registers_every_configured_model(
    db_session, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(settings, "ollama_default_model", "qwen2.5:0.5b")
    monkeypatch.setattr(settings, "ollama_models", "phi3:mini,tinyllama")
    monkeypatch.setattr("app.main.async_session_factory", lambda: _session_factory(db_session))

    await seed_default_model()

    rows = (await db_session.execute(select(ModelConfig))).scalars().all()
    by_name = {row.name: row for row in rows}
    # Every configured model is present, active and length-capped.
    for name in ("qwen2.5:0.5b", "phi3:mini", "tinyllama"):
        assert name in by_name
        assert by_name[name].is_active is True
        assert by_name[name].max_tokens == 1024


async def test_seed_marks_the_configured_default(
    db_session, monkeypatch: pytest.MonkeyPatch
):
    # The default flag must follow OLLAMA_DEFAULT_MODEL, independent of whatever
    # the shared development database happens to contain. Fresh names guarantee
    # the seeder actually creates the rows (it never overwrites existing ones).
    await db_session.execute(update(ModelConfig).values(is_default=False))
    default_name = f"test-default-{uuid.uuid4().hex[:6]}"
    extra_name = f"test-extra-{uuid.uuid4().hex[:6]}"

    monkeypatch.setattr(settings, "ollama_default_model", default_name)
    monkeypatch.setattr(settings, "ollama_models", extra_name)
    monkeypatch.setattr("app.main.async_session_factory", lambda: _session_factory(db_session))

    await seed_default_model()

    by_name = {
        row.name: row
        for row in (await db_session.execute(select(ModelConfig))).scalars().all()
    }
    assert by_name[default_name].is_default is True
    assert by_name[extra_name].is_default is False


async def test_seed_is_idempotent_and_keeps_admin_changes(
    db_session, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(settings, "ollama_default_model", "llama3.2:1b")
    monkeypatch.setattr(settings, "ollama_models", "qwen2.5:0.5b")
    monkeypatch.setattr("app.main.async_session_factory", lambda: _session_factory(db_session))

    await seed_default_model()
    # An admin disables a model and renames it; a second startup must not
    # clobber either change.
    disabled = (
        await db_session.execute(
            select(ModelConfig).where(ModelConfig.name == "qwen2.5:0.5b")
        )
    ).scalar_one()
    disabled.is_active = False
    await db_session.commit()

    await seed_default_model()

    refreshed = (
        await db_session.execute(
            select(ModelConfig).where(ModelConfig.name == "qwen2.5:0.5b")
        )
    ).scalar_one()
    assert refreshed.is_active is False


@asynccontextmanager
async def _session_factory(db_session):
    """Yield the test session so the seeder shares the rolled-back transaction."""
    yield db_session
