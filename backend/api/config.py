"""Application configuration, loaded from environment variables (.env supported).

Keeping this dependency-light (python-dotenv + os.environ) avoids pinning a
settings library this early. Swap for pydantic-settings later if it earns its keep.
"""
from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()  # read a local .env if present; real env vars take precedence


def _env(key: str, default: str) -> str:
    return os.getenv(key, default)


@dataclass(frozen=True)
class Settings:
    app_env: str = _env("APP_ENV", "dev")
    log_level: str = _env("LOG_LEVEL", "INFO")

    # Postgres / TimescaleDB
    # Managed hosts (Render/Railway/Neon…) provide a single DATABASE_URL; if set,
    # it wins over the discrete POSTGRES_* vars.
    database_url: str = _env("DATABASE_URL", "")
    pg_host: str = _env("POSTGRES_HOST", "localhost")
    pg_port: int = int(_env("POSTGRES_PORT", "5432"))
    pg_user: str = _env("POSTGRES_USER", "alphaforge")
    pg_password: str = _env("POSTGRES_PASSWORD", "alphaforge")
    pg_db: str = _env("POSTGRES_DB", "alphaforge")

    # Redis
    redis_url: str = _env("REDIS_URL", "redis://localhost:6379/0")

    # Auth (Phase 9)
    jwt_secret: str = _env("JWT_SECRET", "dev-secret-change-me")
    jwt_ttl_hours: int = int(_env("JWT_TTL_HOURS", "24"))

    # Trading (Phase 9): "paper" fills against the simulator; "live" routes to
    # the Angel One adapter when SMARTAPI_* credentials are present.
    trading_mode: str = _env("TRADING_MODE", "paper")

    # AI (Phase 9): Gemini API key for LLM analysis; blank -> rule-based fallback.
    gemini_api_key: str = _env("GEMINI_API_KEY", "")
    gemini_model: str = _env("GEMINI_MODEL", "gemini-2.5-flash")

    @property
    def pg_dsn(self) -> str:
        if self.database_url:
            # psycopg2 accepts a libpq URI directly (postgres:// or postgresql://)
            return self.database_url
        return (
            f"host={self.pg_host} port={self.pg_port} "
            f"dbname={self.pg_db} user={self.pg_user} password={self.pg_password}"
        )


settings = Settings()
