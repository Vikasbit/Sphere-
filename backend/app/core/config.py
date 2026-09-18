"""
Centralized application configuration.

Uses pydantic-settings to load environment variables from .env file.
All configuration values are accessed through the `settings` singleton.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # MongoDB
    mongodb_uri: str = "mongodb://localhost:27017"
    database_name: str = "spheresphere"

    # JWT
    jwt_secret: str = "change-me-to-a-random-secret-min-32-chars"
    jwt_refresh_secret: str = "change-me-to-another-random-secret-min-32-chars"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    # Environment
    environment: str = "development"

    # URLs & CORS
    frontend_url: str = "http://localhost:5173"
    backend_url: str = "http://localhost:8000"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # Rate Limiting
    rate_limit_enabled: bool = True

    # Cookie settings
    cookie_secure: bool = False
    cookie_samesite: str = "lax"
    cookie_domain: str | None = None
    access_cookie_name: str = "access_token"
    refresh_cookie_name: str = "refresh_token"

    # Telemetry & Privacy
    ip_hash_salt: str = "spheresphere-ip-pepper-secret-32-chars"

    @property
    def is_production(self) -> bool:
        return self.environment.lower() in ("production", "prod")

    @property
    def effective_cookie_secure(self) -> bool:
        """Enforces secure=True if in production, or if cookie_secure is True."""
        if self.cookie_secure:
            return True
        return self.is_production

    @property
    def short_link_base_url(self) -> str:
        """Base URL for short links (e.g., http://localhost:8000/r/)."""
        return f"{self.backend_url}/r"


@lru_cache
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()
