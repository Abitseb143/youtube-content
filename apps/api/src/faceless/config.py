from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Required
    database_url: str = Field(..., description="Postgres async DSN")
    redis_url: str
    s3_bucket: str
    s3_endpoint: str
    s3_access_key: str
    s3_secret_key: str
    clerk_jwt_issuer: str
    clerk_jwt_audience: str
    encryption_key: str = Field(..., description="Base64-encoded 32 bytes for AES-GCM")

    # Optional with defaults
    environment: Literal["dev", "staging", "prod"] = "dev"
    log_level: Literal["debug", "info", "warning", "error"] = "info"
    s3_region: str = "auto"
    api_port: int = 8000
    cors_allow_origins: str = "http://localhost:3000"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
