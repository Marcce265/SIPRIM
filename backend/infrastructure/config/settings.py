from functools import lru_cache
import os

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    app_name: str = "SIPRIM Backend"
    app_env: str = "development"
    use_in_memory_repository: bool = True
    enable_demo_fallback: bool = Field(
        default=False,
        description="Habilita modo demostracion explicitamente para consulta normativa sin PostgreSQL. Desactivado por defecto.",
    )
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/siprim"
    auth_db_url: str = (
        "postgresql+psycopg://auth_app:auth_dev_only@localhost:5432/auth_db"
    )
    platform_db_url: str = (
        "postgresql+psycopg://platform_app:platform_dev_only@localhost:5432/platform_db"
    )
    economic_db_url: str = (
        "postgresql+psycopg://economic_app:economic_dev_only@localhost:5432/economic_db"
    )
    redis_url: str = "redis://localhost:6379/0"
    jwt_secret: SecretStr = SecretStr("cambiar-esta-clave-segura-en-produccion")
    jwt_issuer: str = "siprim-auth"
    jwt_audience: str = "siprim-api"
    jwt_expiration_minutes: int = Field(default=60, gt=0, le=1440)
    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]
    gemini_api_key: SecretStr | None = None
    ai_model: str = Field(default="gemini-3.1-flash-lite", min_length=1)
    ai_timeout_seconds: float = Field(default=45, gt=0, le=120)


    @model_validator(mode="after")
    def validate_production_secret(self):
        if self.app_env.lower() in {"production", "preview"} or os.environ.get("VERCEL") == "1":
            secret = self.jwt_secret.get_secret_value()
            if len(secret.encode()) < 32 or secret in {
                "cambiar-esta-clave-segura-en-produccion",
                "solo-desarrollo-cambiar-en-produccion",
            }:
                raise ValueError("JWT_SECRET debe ser una clave propia de al menos 32 bytes en produccion")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
