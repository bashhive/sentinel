"""
Configuration management for Aspasia.

Loads environment variables, validates settings, and provides config access.
"""

import os
from typing import Optional
from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import Field, validator


class Config(BaseSettings):
    """Configuration for Aspasia bot."""

    # Claude API
    claude_api_key: str = Field(..., alias="CLAUDE_API_KEY")
    claude_model: str = Field(
        default="claude-3-5-sonnet-20241022", alias="CLAUDE_MODEL"
    )
    claude_max_tokens: int = Field(default=2048, alias="CLAUDE_MAX_TOKENS")

    # Agent
    agent_name: str = Field(default="Aspasia", alias="AGENT_NAME")
    agent_memory_size: int = Field(default=50, alias="AGENT_MEMORY_SIZE")
    agent_timeout_seconds: int = Field(default=30, alias="AGENT_TIMEOUT_SECONDS")

    # Telegram
    telegram_bot_token: Optional[str] = Field(
        default=None, alias="TELEGRAM_BOT_TOKEN"
    )
    telegram_webhook_url: Optional[str] = Field(
        default=None, alias="TELEGRAM_WEBHOOK_URL"
    )
    telegram_webhook_secret: Optional[str] = Field(
        default=None, alias="TELEGRAM_WEBHOOK_SECRET"
    )

    # Web Server
    web_host: str = Field(default="0.0.0.0", alias="WEB_HOST")
    web_port: int = Field(default=8000, alias="WEB_PORT")
    web_debug: bool = Field(default=False, alias="WEB_DEBUG")
    web_cors_origins: str = Field(
        default="http://localhost:3000", alias="WEB_CORS_ORIGINS"
    )
    web_api_key: Optional[str] = Field(default=None, alias="WEB_API_KEY")

    # Database
    database_url: str = Field(
        default="sqlite:///./aspasia.db", alias="DATABASE_URL"
    )

    # Redis
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")
    redis_enabled: bool = Field(default=False, alias="REDIS_ENABLED")

    # Logging
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    log_format: str = Field(default="json", alias="LOG_FORMAT")
    log_file: str = Field(default="./logs/aspasia.log", alias="LOG_FILE")

    # Security
    allow_admin_endpoints: bool = Field(default=True, alias="ALLOW_ADMIN_ENDPOINTS")
    require_api_key: bool = Field(default=False, alias="REQUIRE_API_KEY")

    # Environment
    environment: str = Field(default="development", alias="ENVIRONMENT")

    class Config:
        env_file = ".env"
        case_sensitive = False

    @validator("log_level")
    def validate_log_level(cls, v):
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if v.upper() not in valid_levels:
            raise ValueError(f"Log level must be one of {valid_levels}")
        return v.upper()

    @validator("environment")
    def validate_environment(cls, v):
        valid_envs = {"development", "staging", "production"}
        if v.lower() not in valid_envs:
            raise ValueError(f"Environment must be one of {valid_envs}")
        return v.lower()

    @property
    def is_production(self) -> bool:
        """Check if running in production."""
        return self.environment == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development."""
        return self.environment == "development"

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse CORS origins from comma-separated string."""
        return [origin.strip() for origin in self.web_cors_origins.split(",")]

    def ensure_log_dir(self) -> None:
        """Ensure log directory exists."""
        log_dir = Path(self.log_file).parent
        log_dir.mkdir(parents=True, exist_ok=True)

    def validate_required_keys(self) -> None:
        """Validate that all required API keys are present."""
        if not self.claude_api_key:
            raise ValueError("CLAUDE_API_KEY is required")

        # Telegram is optional but must have both token and webhook URL if one is set
        if (self.telegram_bot_token or self.telegram_webhook_url) and not (
            self.telegram_bot_token and self.telegram_webhook_url
        ):
            raise ValueError(
                "Both TELEGRAM_BOT_TOKEN and TELEGRAM_WEBHOOK_URL must be set together"
            )


def get_config() -> Config:
    """Load and return configuration."""
    config = Config()
    config.ensure_log_dir()
    config.validate_required_keys()
    return config
