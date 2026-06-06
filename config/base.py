"""
Base infrastructure settings.
Persona/profile settings live in profiles/<name>/profile.py — not here.

LLM provider is pluggable and FREE-tier-first:
  LLM_PROVIDER=groq   (default)  -> Groq OpenAI-compatible API (free tier)
  LLM_PROVIDER=gemini            -> set LLM_BASE_URL to Gemini's OpenAI endpoint
  LLM_PROVIDER=openrouter|local  -> any OpenAI-compatible base_url
  LLM_PROVIDER=anthropic         -> paid Anthropic SDK (optional)
"""

from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class BaseConfig(BaseSettings):
    """
    Infrastructure-level settings loaded from environment variables.
    Profiles inject agent_name, system_prompt, etc. separately.
    """

    # ── LLM provider selection ────────────────────────────────────────────────
    llm_provider: str = Field("groq", alias="LLM_PROVIDER")
    # Default model is a Groq free-tier model that supports tool-calling.
    agent_model: str = Field("llama-3.3-70b-versatile", alias="AGENT_MODEL")
    # Cheap/fast model used only for the health-check ping.
    probe_model: str = Field("llama-3.1-8b-instant", alias="PROBE_MODEL")
    # Optional override of the OpenAI-compatible endpoint (Gemini/OpenRouter/local).
    llm_base_url: Optional[str] = Field(None, alias="LLM_BASE_URL")

    # API keys — all optional; the factory validates the one actually selected.
    groq_api_key: Optional[str] = Field(None, alias="GROQ_API_KEY")
    # Generic alias for any OpenAI-compatible provider (falls back to GROQ_API_KEY).
    llm_api_key: Optional[str] = Field(None, alias="LLM_API_KEY")
    anthropic_api_key: Optional[str] = Field(None, alias="ANTHROPIC_API_KEY")

    max_tokens: int = Field(1024, alias="MAX_TOKENS")
    temperature: float = Field(0.5, alias="TEMPERATURE")
    memory_size: int = Field(30, alias="MEMORY_SIZE")

    # ── Web server ────────────────────────────────────────────────────────────
    host: str = Field("0.0.0.0", alias="HOST")
    port: int = Field(8000, alias="PORT")
    debug: bool = Field(False, alias="DEBUG")

    # ── Optional channels ─────────────────────────────────────────────────────
    telegram_bot_token: Optional[str] = Field(None, alias="TELEGRAM_BOT_TOKEN")
    telegram_webhook_url: Optional[str] = Field(None, alias="TELEGRAM_WEBHOOK_URL")

    # ── Optional infra ────────────────────────────────────────────────────────
    redis_url: Optional[str] = Field(None, alias="REDIS_URL")
    database_url: Optional[str] = Field(None, alias="DATABASE_URL")

    # ── Runtime ───────────────────────────────────────────────────────────────
    environment: str = Field("development", alias="ENVIRONMENT")
    log_level: str = Field("INFO", alias="LOG_LEVEL")

    # Active profile (resolved at startup)
    profile: str = Field("bash_pt", alias="PROFILE")

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def resolved_llm_key(self) -> Optional[str]:
        """Single source of truth for the OpenAI-compatible API key."""
        return self.groq_api_key or self.llm_api_key

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
