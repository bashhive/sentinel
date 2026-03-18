"""
Aspasia Configuration Management
"""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings from environment variables"""
    
    # Claude API
    anthropic_api_key: str
    
    # Telegram
    telegram_bot_token: str
    telegram_webhook_url: Optional[str] = None
    
    # Web Server
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    
    # Redis
    redis_url: Optional[str] = None
    
    # Agent Configuration
    agent_name: str = "Aspasia"
    agent_model: str = "claude-3-5-sonnet-20241022"
    max_tokens: int = 2048
    temperature: float = 0.7
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

# Load settings
settings = Settings()
