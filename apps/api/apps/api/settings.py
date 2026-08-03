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

    database_url: str = "postgresql+asyncpg://postgres:chronoarb@localhost:5432/chronoarb"


settings = Settings()
