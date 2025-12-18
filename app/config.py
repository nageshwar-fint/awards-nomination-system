from functools import lru_cache
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # App settings
    app_env: str = Field(default="local", alias="APP_ENV")
    app_port: int = Field(default=8000, alias="APP_PORT")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    # Database
    database_url: str = Field(..., alias="DATABASE_URL")

    # JWT settings
    jwt_secret: str = Field(..., alias="JWT_SECRET")
    jwt_issuer: str = Field(default="awards-nomination-system", alias="JWT_ISSUER")
    jwt_audience: str = Field(default="awards-nomination-system", alias="JWT_AUDIENCE")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    jwt_access_token_expire_minutes: int = Field(default=30, alias="JWT_ACCESS_TOKEN_EXPIRE_MINUTES")

    # CORS
    cors_origins: str = Field(default="*", alias="CORS_ORIGINS")

    # Idempotency
    idempotency_ttl_seconds: int = Field(default=300, alias="IDEMPOTENCY_TTL_SECONDS")

    # Seeding
    seed_on_start: bool = Field(default=False, alias="SEED_ON_START")

    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins from comma-separated string or '*'."""
        if self.cors_origins == "*":
            return ["*"]
        return [origin.strip() for origin in self.cors_origins.split(",")]

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.app_env.lower() == "production"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
