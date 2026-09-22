"""FastAPI application entrypoint.

Wires the whole backend together: logging, CORS, middleware, exception
handlers and the versioned API router. On first startup it provisions the
default administrator from configuration.
"""

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, select

from app.api import api_router
from app.api.health import router as health_router
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import get_logger, setup_logging
from app.core.middleware import register_middleware
from app.core.redis import close_redis
from app.core.security import hash_password
from app.database.connection import async_session_factory, dispose_engine
from app.models import UserRole
from app.models.user import User
from app.services.usage_service import UsageService
from app.models.model import ModelConfig, ModelProvider, ModelType

logger = get_logger(__name__)

API_VERSION = "1.0.0"


async def seed_admin() -> None:
    """Create the configured default administrator (idempotent)."""
    async with async_session_factory() as db:
        existing = await db.execute(
            select(User).where(User.email == settings.default_admin_email)
        )
        if existing.scalar_one_or_none() is not None:
            return

        admin = User(
            email=settings.default_admin_email,
            password_hash=hash_password(settings.default_admin_password),
            name=settings.default_admin_name,
            role=UserRole.ADMIN,
        )
        db.add(admin)
        await db.flush()
        await UsageService(db).create_for_user(admin.id)
        await db.commit()
        logger.info("Seeded default administrator: %s", admin.email)


async def seed_default_model() -> None:
    """Register the configured Ollama models in the catalog (idempotent).

    Keeps the chat UI's model dropdown working out of the box: the model set
    through ``OLLAMA_DEFAULT_MODEL`` appears as an active catalog entry, plus
    any extra models listed in ``OLLAMA_MODELS``. An entry that already exists
    (even if an admin disabled it) is never overwritten, so administrative
    changes always win.
    """
    names = _configured_model_names()
    if not names:
        return

    async with async_session_factory() as db:
        already = await db.execute(
            select(ModelConfig.name).where(ModelConfig.name.in_(names))
        )
        missing = names - {row[0] for row in already}

        # Only the configured default model becomes the catalog default, and
        # only when no default exists at all.
        has_default = (
            await db.scalar(
                select(func.count())
                .select_from(ModelConfig)
                .where(ModelConfig.is_default.is_(True))
            )
            or 0
        ) == 0

        for model_name in sorted(missing):
            db.add(
                ModelConfig(
                    name=model_name,
                    provider=ModelProvider.OLLAMA,
                    model_identifier=model_name,
                    model_type=ModelType.CHAT,
                    is_active=True,
                    is_default=has_default and model_name == settings.ollama_default_model,
                    # Bounds the generated length (Ollama's ``num_predict``).
                    # The column default is 128000, which on CPU-only hardware
                    # lets a model ramble for minutes; 1024 is a generous chat
                    # cap.
                    max_tokens=1024,
                )
            )
        await db.commit()
        for model_name in sorted(missing):
            logger.info("Seeded Ollama model: %s", model_name)


def _configured_model_names() -> set[str]:
    """The default model plus any extra models from ``OLLAMA_MODELS``."""
    names = {settings.ollama_default_model} if settings.ollama_default_model else set()
    for extra in settings.ollama_models.split(","):
        extra = extra.strip()
        if extra:
            names.add(extra)
    return names


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application startup/shutdown lifecycle."""
    setup_logging(debug=settings.debug, is_production=settings.is_production)
    logger.info(
        "Starting %s (env=%s, version=%s)",
        settings.app_name,
        settings.app_env,
        API_VERSION,
    )
    await seed_admin()
    await seed_default_model()
    logger.info("Ready — listening for requests")
    yield
    logger.info("Shutting down: disposing DB pool and Redis client")
    await dispose_engine()
    await close_redis()


app = FastAPI(
    title=settings.app_name,
    description=(
        "REST API for the AI Agent Platform. All endpoints are versioned under "
        "`/api/v1`. Authentication uses JWT bearer tokens obtained from "
        "`/api/v1/auth/login`. Interactive docs are available at `/docs`."
    ),
    version=API_VERSION,
    lifespan=lifespan,
    openapi_tags=[
        {"name": "health", "description": "Liveness and readiness probes"},
        {"name": "auth", "description": "Registration, login and token refresh"},
        {"name": "chat", "description": "Chat completion and conversations"},
        {"name": "users", "description": "Profile and user management"},
        {"name": "models", "description": "Model catalog"},
        {"name": "usage", "description": "Usage allowance and history"},
        {"name": "tools", "description": "Tool catalog"},
        {"name": "admin", "description": "Administrative endpoints"},
    ],
)

# Middleware is registered in a fixed order (see app.core.middleware).
register_middleware(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)

# Everything lives under /api/v1 so a future v2 can ship without breaking
# the existing frontend.
app.include_router(api_router)

# Probes stay outside the version prefix so infrastructure tools can reach
# them regardless of API versioning.
app.include_router(health_router)


@app.get("/", include_in_schema=False)
async def root() -> dict[str, str]:
    """Small landing payload pointing to the interactive docs."""
    return {
        "name": settings.app_name,
        "version": API_VERSION,
        "docs": "/docs",
        "health": "/health",
    }
