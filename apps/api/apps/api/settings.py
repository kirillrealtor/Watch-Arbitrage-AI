from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="CHRONOARB_",
        extra="ignore",
    )

    app_name: str = "ChronoArb"
    app_version: str = "0.1.0"
    debug: bool = False
    log_level: str = "INFO"

    # Default is SQLite (aiosqlite) for local development.
    # PostgreSQL async drivers (asyncpg, psycopg) have unresolved compatibility
    # issues with Python 3.14 as of 2026-08-03. Production must override via
    # CHRONOARB_DATABASE_URL=postgresql+asyncpg://... (CI runs Python 3.13).
    database_url: str = "sqlite+aiosqlite:///chronoarb.db"


settings = Settings()
