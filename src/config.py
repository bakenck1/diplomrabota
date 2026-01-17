"""Application configuration using pydantic-settings."""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Application
    app_name: str = "Voice Assistant Pipeline"
    debug: bool = False
    environment: Literal["development", "staging", "production"] = "development"

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/voice_assistant"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Object Storage (S3/MinIO)
    s3_endpoint_url: str = "http://localhost:9000"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_bucket_name: str = "voice-assistant"
    s3_url_expiration_seconds: int = 3600

    # OpenAI
    openai_api_key: str = ""

    # Google Cloud
    google_application_credentials: str = ""
    google_api_key: str = ""

    # JWT Auth
    jwt_secret_key: str = "your-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60

    # Normalization
    normalization_confidence_threshold: float = 0.7
    normalization_fuzzy_max_distance: int = 2

    # Retention
    audio_retention_days: int = 90


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
