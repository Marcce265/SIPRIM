from functools import lru_cache
from pathlib import Path
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Sistema Multiagente - Priorizacion Municipal"
    app_env: str = "development"
    gemini_api_key: SecretStr | None = None
    ai_model: str = Field(default="gemini-2.5-flash", min_length=1)
    ai_timeout_seconds: float = Field(default=45, gt=0, le=120)
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: SecretStr | None = None
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/proyectos"
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[3] / ".env",
        env_file_encoding="utf-8", extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
