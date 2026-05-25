"""
Phalit.ai · centralized configuration.

All runtime config is loaded from environment variables on startup via
Pydantic's BaseSettings. Required vars are validated at import time —
if any are missing or empty, the app refuses to start with a clear error
showing exactly which var is missing.

Production: set env vars in Render.com → your-service → Environment tab.
Local dev:  set env vars in your shell, or create a .env file (see .env.example).

Usage from other modules:
    from config import get_settings
    settings = get_settings()
    print(settings.supabase_url)
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import BaseSettings, Field, validator


class Settings(BaseSettings):
    """Phalit.ai runtime configuration. Loaded once per process."""

    # ----- Supabase -----
    supabase_url: str = Field(
        ...,
        env="SUPABASE_URL",
        description="e.g. https://zrcrrtrvyldzaqukwzge.supabase.co",
    )
    supabase_publishable_key: str = Field(
        ...,
        env="SUPABASE_PUBLISHABLE_KEY",
        description="sb_publishable_... — public, frontend-safe",
    )
    supabase_secret_key: str = Field(
        ...,
        env="SUPABASE_SECRET_KEY",
        description="sb_secret_... — backend only, bypasses RLS",
    )

    # ----- JWT verification tuning (optional, sensible defaults) -----
    jwt_cache_ttl_seconds: int = Field(
        900,
        env="JWT_CACHE_TTL_SECONDS",
        description="How long to cache JWKS keys before re-fetching",
    )
    jwt_http_timeout_seconds: float = Field(
        5.0,
        env="JWT_HTTP_TIMEOUT_SECONDS",
        description="Timeout when fetching JWKS from Supabase",
    )

    # ----- Environment label (optional, for logging/behavior gating) -----
    environment: str = Field(
        "production",
        env="PHALIT_ENV",
        description="One of: development, staging, production",
    )

    @validator("supabase_url")
    def _strip_trailing_slash(cls, v: str) -> str:
        if not v:
            raise ValueError("SUPABASE_URL cannot be empty")
        return v.rstrip("/")

    @validator(
        "supabase_publishable_key",
        "supabase_secret_key",
    )
    def _non_empty_key(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Supabase key cannot be empty")
        return v.strip()

    @validator("environment")
    def _normalize_environment(cls, v: str) -> str:
        v = v.lower().strip()
        if v not in {"development", "staging", "production"}:
            raise ValueError(
                f"PHALIT_ENV must be development/staging/production, got: {v!r}"
            )
        return v

    class Config:
        case_sensitive = False
        env_file = ".env"  # honored only if python-dotenv is installed; ignored on Render
        env_file_encoding = "utf-8"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Returns a singleton Settings instance.
    Cached so env vars are only parsed once per process.
    """
    return Settings()
