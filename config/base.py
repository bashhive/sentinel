"""
Base infrastructure settings.
Persona/profile settings live in profiles/<name>/profile.py — not here.
"""

from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class BaseConfig(BaseSettings):
    """
    Infrastructure-level settings loaded from environment variables.
    Profiles inject agent_name, system_prompt, etc. separately.
    """

    # Anthropic
    anthropic_api_key: str = Field(..., alias="ANTHROPIC_API_KEY")
    agent_model: str = Field("claude-3-5-sonnet-20241022", alias="AGENT_MODEL")
    max_tokens: int = Field(2048, alias="MAX_TOKENS")
    temperature: float = Field(0.7, alias="TEMPERATURE")
    memory_size: int = Field(50, alias="MEMORY_SIZE")

    # Web server
    host: str = Field("0.0.0.0", alias="HOST")
    port: int = Field(8000, alias="PORT")
    debug: bool = Field(False, alias="DEBUG")

    # Optional channels
    telegram_bot_token: Optional[str] = Field(None, alias="TELEGRAM_BOT_TOKEN")
    telegram_webhook_url: Optional[str] = Field(None, alias="TELEGRAM_WEBHOOK_URL")

    # Optional infra
    redis_url: Optional[str] = Field(None, alias="REDIS_URL")
    database_url: Optional[str] = Field(None, alias="DATABASE_URL")

    # Runtime
    environment: str = Field("development", alias="ENVIRONMENT")
    log_level: str = Field("INFO", alias="LOG_LEVEL")

    # Active profile (resolved at startup)
    profile: str = Field("aspasia_default", alias="PROFILE")

    class Config:
        env_file = ".env"
        case_sensitive = False

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    def to_agent_config(self, profile_overrides: dict = None) -> dict:
        """
        Merge infra settings with profile overrides into agent config dict.
        Profile values take precedence over infra defaults.
        """
        base = {
            "model": self.agent_model,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "memory_size": self.memory_size,
        }
        if profile_overrides:
            base.update(profile_overrides)
        return base


def load_config() -> BaseConfig:
    return BaseConfig()
