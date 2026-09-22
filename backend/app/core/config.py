"""Application configuration.

All environment-specific configuration is loaded from a `.env` file via
pydantic-settings. No secrets are hard-coded in source code.
"""

from functools import lru_cache
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central settings object for the whole application."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Application ---
    app_name: str = "AI Agent Platform"
    app_env: Literal["development", "staging", "production"] = "development"
    debug: bool = False

    # --- PostgreSQL ---
    database_url: str = (
        "postgresql+asyncpg://postgres:postgres@localhost:5432/ai_agent"
    )

    # Connection pool
    db_pool_size: int = 10
    db_max_overflow: int = 20
    db_pool_timeout: int = 30
    db_pool_recycle: int = 1800

    # --- Redis ---
    redis_url: str = "redis://localhost:6379/0"

    # --- JWT / Auth ---
    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # --- Default admin (seeded on first startup only) ---
    default_admin_email: str = "admin@example.com"
    default_admin_password: str = "change-me-now"
    default_admin_name: str = "Admin"

    # --- Rate limiting ---
    rate_limit_per_minute: int = 60
    rate_limit_per_hour: int = 1000

    # --- CORS ---
    cors_origins: str = "http://localhost:3000,http://localhost:5173"

    # --- LLM provider ---
    # Name of the provider the chat service routes to. New providers are
    # registered in app/llm/factory.py; the API/service layers never change.
    llm_provider: str = "ollama"
    # Base URL of the Ollama HTTP API. When the backend runs in Docker and
    # Ollama runs on the host, use http://host.docker.internal:11434 instead
    # of localhost (a container's localhost is not the host's localhost).
    ollama_base_url: str = "http://localhost:11434"
    # Model used when the request does not name one and no default is set in
    # the model catalog. Set this to a model you have pulled locally. On
    # CPU-only machines smaller models are much faster (see README).
    ollama_default_model: str = "qwen2.5:0.5b"
    # Extra models (comma separated) registered in the catalog at startup so
    # they appear in the chat UI's model dropdown. They must be pulled locally,
    # e.g. OLLAMA_MODELS=qwen2.5:0.5b,llama3.2:3b
    ollama_models: str = ""
    # Per-request timeout (seconds) for Ollama calls. Generations are slow, so
    # this is deliberately larger than the default API timeout. This must stay
    # >= the frontend chat timeout and the Nginx proxy timeout, otherwise a
    # valid but slow response is killed mid-flight.
    ollama_request_timeout: float = 180.0
    # How long Ollama keeps the model loaded after a request (Ollama duration
    # string). Reloading a model from disk costs tens of seconds on CPU-only
    # machines, so keeping it warm removes that penalty from later requests.
    # Set to "0" to unload immediately after every request.
    ollama_keep_alive: str = "30m"

    @property
    def cors_origin_list(self) -> list[str]:
        """Parse the comma-separated CORS origins into a list."""
        return [
            origin.strip()
            for origin in self.cors_origins.split(",")
            if origin.strip()
        ]

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, value: str) -> str:
        """Guarantee the asyncpg driver is used for async SQLAlchemy."""
        if value.startswith("postgresql://"):
            return value.replace(
                "postgresql://", "postgresql+asyncpg://", 1
            )
        return value

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    """Return a cached settings instance (created once per process)."""
    return Settings()


settings = get_settings()
