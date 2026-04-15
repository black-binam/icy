"""Application settings (Pydantic v2)."""
from __future__ import annotations

import base64
from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration loaded from environment / .env."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )

    # App
    APP_NAME: str = "HealthcareRouteOptimizer"
    ENVIRONMENT: Literal["development", "staging", "production", "test"] = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"

    # Security
    SECRET_KEY: str = Field(min_length=32)
    FIELD_ENCRYPTION_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    JWT_ALGORITHM: str = "HS256"

    # Database
    DATABASE_URL: str = "postgresql+psycopg://icy:icy_dev_password_change_me@localhost:5432/icy"

    # Redis / Celery
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    # Routing
    ROUTING_PROVIDER: Literal["haversine", "osrm", "openrouteservice"] = "haversine"
    OSRM_BASE_URL: str = "http://localhost:5000"
    OPENROUTESERVICE_API_KEY: str = ""

    # CORS
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"
    CORS_ALLOW_CREDENTIALS: bool = False

    # Rate limit
    LOGIN_RATE_LIMIT: str = "5/minute"

    @field_validator("FIELD_ENCRYPTION_KEY")
    @classmethod
    def _check_fernet_key(cls, v: str) -> str:
        """Ensure the Fernet key decodes to exactly 32 raw bytes (urlsafe-base64)."""
        try:
            raw = base64.urlsafe_b64decode(v.encode("ascii"))
        except Exception as exc:
            raise ValueError("FIELD_ENCRYPTION_KEY must be urlsafe-base64 encoded") from exc
        if len(raw) != 32:
            raise ValueError("FIELD_ENCRYPTION_KEY must decode to 32 bytes")
        return v

    @field_validator("SECRET_KEY")
    @classmethod
    def _check_secret_key(cls, v: str, info) -> str:
        env = info.data.get("ENVIRONMENT", "development")
        if env == "production" and len(v) < 32:
            raise ValueError("SECRET_KEY must be >=32 characters in production")
        return v

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached settings accessor."""
    return Settings()  # type: ignore[call-arg]
