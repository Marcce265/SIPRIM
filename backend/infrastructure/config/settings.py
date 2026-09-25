from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    app_name: str = "SIPRIM Backend"
    app_env: str = "development"
    use_in_memory_repository: bool = True
    database_url: str = (
        "postgresql+psycopg://postgres:postgres@localhost:5432/siprim"
    )
    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
    ]
    gemini_api_key: SecretStr | None = None
    ai_model: str = Field(default="gemini-2.5-flash", min_length=1)
    ai_timeout_seconds: float = Field(default=45, gt=0, le=120)


@lru_cache
def get_settings() -> Settings:
    return Settings()
