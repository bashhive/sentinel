"""
Claude AI API integration.

Handles communication with Anthropic's Claude API.
"""

import logging
from typing import Optional, Any
import httpx
from anthropic import Anthropic, AsyncAnthropic

logger = logging.getLogger(__name__)


class ClaudeAPI:
    """Interface to Anthropic's Claude API."""

    def __init__(self, api_key: str, timeout: int = 30):
        """
        Initialize Claude API client.

        Args:
            api_key: Anthropic API key
            timeout: Request timeout in seconds
        """
        self.api_key = api_key
        self.timeout = timeout
        self.client = Anthropic(api_key=api_key)
        self.async_client = AsyncAnthropic(api_key=api_key)

    async def chat(
        self,
        messages: list[dict],
        model: str,
        system: Optional[str] = None,
        max_tokens: int = 1024,
        tools: Optional[list[dict]] = None,
        temperature: float = 0.7,
    ) -> str:
        """
        Send a chat message to Claude and get a response.

        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model identifier (e.g., 'claude-3-5-sonnet-20241022')
            system: System prompt
            max_tokens: Maximum tokens in response
            tools: Optional list of tool definitions
            temperature: Sampling temperature (0-1)

        Returns:
            Response text from Claude
        """
        try:
            logger.debug(f"Calling Claude API with model {model}")

            response = await self.async_client.messages.create(
                model=model,
                max_tokens=max_tokens,
                system=system,
                messages=messages,
                tools=tools if tools else None,
                temperature=temperature,
            )

            # Extract text from response
            text_blocks = [
                block.text for block in response.content if hasattr(block, "text")
            ]
            result = "\n".join(text_blocks) if text_blocks else ""

            logger.debug(f"Claude response received: {len(result)} chars")
            return result

        except Exception as e:
            logger.error(f"Claude API error: {str(e)}")
            raise

    def chat_sync(
        self,
        messages: list[dict],
        model: str,
        system: Optional[str] = None,
        max_tokens: int = 1024,
        tools: Optional[list[dict]] = None,
        temperature: float = 0.7,
    ) -> str:
        """
        Synchronous version of chat.

        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model identifier
            system: System prompt
            max_tokens: Maximum tokens in response
            tools: Optional list of tool definitions
            temperature: Sampling temperature (0-1)

        Returns:
            Response text from Claude
        """
        try:
            logger.debug(f"Calling Claude API (sync) with model {model}")

            response = self.client.messages.create(
                model=model,
                max_tokens=max_tokens,
                system=system,
                messages=messages,
                tools=tools if tools else None,
                temperature=temperature,
            )

            # Extract text from response
            text_blocks = [
                block.text for block in response.content if hasattr(block, "text")
            ]
            result = "\n".join(text_blocks) if text_blocks else ""

            logger.debug(f"Claude response received: {len(result)} chars")
            return result

        except Exception as e:
            logger.error(f"Claude API error: {str(e)}")
            raise

    async def health_check(self) -> bool:
        """
        Check if Claude API is accessible.

        Returns:
            True if accessible, raises exception otherwise
        """
        try:
            # Make a minimal request to check connectivity
            response = await self.async_client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=10,
                messages=[{"role": "user", "content": "test"}],
            )
            logger.info("Claude API health check passed")
            return True
        except Exception as e:
            logger.error(f"Claude API health check failed: {str(e)}")
            raise

    def get_model_info(self, model: str) -> dict:
        """
        Get information about a Claude model.

        Returns:
            Model information dict
        """
        models = {
            "claude-3-5-sonnet-20241022": {
                "name": "Claude 3.5 Sonnet",
                "context_window": 200000,
                "max_output": 4096,
                "description": "Fast, powerful model for most tasks",
            },
            "claude-3-opus-20250219": {
                "name": "Claude 3 Opus",
                "context_window": 200000,
                "max_output": 4096,
                "description": "Most capable model for complex tasks",
            },
            "claude-3-haiku-20250307": {
                "name": "Claude 3 Haiku",
                "context_window": 200000,
                "max_output": 4096,
                "description": "Fast, compact model for simple tasks",
            },
        }

        return models.get(
            model,
            {
                "name": model,
                "context_window": 200000,
                "max_output": 4096,
                "description": "Unknown model",
            },
        )
