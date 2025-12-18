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

    # Email settings (for password reset)
    smtp_host: str = Field(default="localhost", alias="SMTP_HOST")
    smtp_port: int = Field(default=587, alias="SMTP_PORT")
    smtp_user: str = Field(default="", alias="SMTP_USER")
    smtp_password: str = Field(default="", alias="SMTP_PASSWORD")
    smtp_from_email: str = Field(default="noreply@awards-system.com", alias="SMTP_FROM_EMAIL")
    smtp_use_tls: bool = Field(default=True, alias="SMTP_USE_TLS")
    
    # Password reset settings
    password_reset_token_expire_hours: int = Field(default=1, alias="PASSWORD_RESET_TOKEN_EXPIRE_HOURS")
    frontend_base_url: str = Field(default="http://localhost:3000", alias="FRONTEND_BASE_URL")

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
