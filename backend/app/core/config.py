
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "DevPilot AI"
    app_env: str = "development"
    app_host: str = "127.0.0.1"
    app_port: int = 8000

    database_url: str | None = None

    llm_provider: str = "mock"
    nebius_api_key: str | None = None
    nebius_base_url: str | None = None
    nebius_model: str | None = None

    sandbox_provider: str = "mock"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
