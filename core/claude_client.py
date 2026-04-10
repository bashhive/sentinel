"""
Claude API client — async/sync wrapper over Anthropic SDK.
No business logic here; pure transport layer.
"""

import logging
from typing import Optional
from anthropic import Anthropic, AsyncAnthropic

logger = logging.getLogger(__name__)


class ClaudeClient:
    """Thin async/sync wrapper for the Anthropic Messages API."""

    def __init__(self, api_key: str, timeout: int = 30):
        self.api_key = api_key
        self.timeout = timeout
        self._sync = Anthropic(api_key=api_key)
        self._async = AsyncAnthropic(api_key=api_key)

    async def chat(
        self,
        messages: list[dict],
        model: str,
        system: Optional[str] = None,
        max_tokens: int = 2048,
        tools: Optional[list[dict]] = None,
        temperature: float = 0.7,
    ) -> str:
        """Async chat — returns response text."""
        try:
            response = await self._async.messages.create(
                model=model,
                max_tokens=max_tokens,
                system=system,
                messages=messages,
                tools=tools or None,
                temperature=temperature,
            )
            return "".join(
                block.text for block in response.content if hasattr(block, "text")
            )
        except Exception as e:
            logger.error(f"ClaudeClient.chat error: {e}")
            raise

    def chat_sync(
        self,
        messages: list[dict],
        model: str,
        system: Optional[str] = None,
        max_tokens: int = 2048,
        tools: Optional[list[dict]] = None,
        temperature: float = 0.7,
    ) -> str:
        """Sync chat — returns response text."""
        try:
            response = self._sync.messages.create(
                model=model,
                max_tokens=max_tokens,
                system=system,
                messages=messages,
                tools=tools or None,
                temperature=temperature,
            )
            return "".join(
                block.text for block in response.content if hasattr(block, "text")
            )
        except Exception as e:
            logger.error(f"ClaudeClient.chat_sync error: {e}")
            raise

    async def health_check(self) -> bool:
        """Minimal liveness check against the API."""
        await self._async.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=10,
            messages=[{"role": "user", "content": "ping"}],
        )
        return True
