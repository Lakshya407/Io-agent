"""API router aggregation.

Every feature router is mounted here under its ``/api/v1`` prefix so the
versioning lives in a single place and ``app.main`` only includes one router.
Liveness/readiness probes are mounted at the application root (outside the
version prefix) in ``app.main`` so infrastructure tools can reach them.
"""

from fastapi import APIRouter

from app.api import admin, chat, models, tools, usage, users
from app.api.auth import router as auth_router

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth_router, prefix="/auth")
api_router.include_router(chat.router, prefix="")
api_router.include_router(users.router, prefix="/users")
api_router.include_router(models.router, prefix="/models")
api_router.include_router(usage.router, prefix="/usage")
api_router.include_router(tools.router, prefix="/tools")
api_router.include_router(admin.router, prefix="/admin")

__all__ = ["api_router"]
