"""Application configuration, loaded from environment variables / .env."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Centralized app settings.

    Pydantic Settings reads from environment variables first and falls back to
    the `.env` file, so the same code runs unmodified in local dev, CI, and
    containers - only the environment changes.
    """

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- General ---
    project_name: str = "AI Inventory Management System"
    api_v1_prefix: str = "/api/v1"
    environment: str = "development"
    debug: bool = True

    # --- Database ---
    database_url: str = "postgresql+psycopg://inventory:inventory@localhost:5432/inventory"
    # A separate database so the test suite's schema drop/create never touches
    # real data - see docs/ARCHITECTURE.md's testing strategy.
    test_database_url: str = (
        "postgresql+psycopg://inventory:inventory@localhost:5432/inventory_test"
    )

    # --- Auth ---
    # Dev-only fallback. Every non-local environment must set a real SECRET_KEY
    # (e.g. `openssl rand -hex 32`) - anyone who can read this default could
    # forge access tokens.
    secret_key: str = "insecure-dev-secret-change-me-00000000000000"
    access_token_expire_minutes: int = 60

    # --- CORS ---
    # Comma-separated list of allowed origins for the frontend dev server / deployment.
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    # --- File storage ---
    # Where uploaded files (product images) are written; served at /static.
    # See app/core/storage.py for why this is local-disk rather than S3.
    upload_dir: str = "uploads"

    # --- ML ---
    # Where the trained demand-forecasting model (Milestone 12) is
    # persisted between the training request and later prediction requests.
    ml_model_dir: str = "ml_artifacts"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance.

    Cached so Settings is only parsed/validated once per process, and so it can
    be swapped via `app.dependency_overrides` in tests.
    """
    return Settings()
