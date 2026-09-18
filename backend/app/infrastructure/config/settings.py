from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Sistema Multiagente - Priorizacion Municipal"
    app_env: str = "development"
    ai_provider: str = "gemini"
    ai_fallback_provider: str = "openai"

    openai_api_key: str | None = None
    openai_model: str = "gpt-4.1-mini"

    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.5-flash"

    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str | None = None

    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/proyectos"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
