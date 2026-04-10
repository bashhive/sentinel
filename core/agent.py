"""
Core Agent — orchestrates Claude, memory, and tools.
No imports from adapters/ or profiles/.
"""

import logging
from datetime import datetime
from typing import Any, Optional

from .claude_client import ClaudeClient
from .session import MemorySystem
from .tools import ToolRegistry

logger = logging.getLogger(__name__)


class AgentResponse:
    def __init__(self, text: str, user_id: str, metadata: dict = None):
        self.text = text
        self.user_id = user_id
        self.timestamp = datetime.now()
        self.metadata = metadata or {}

    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "user_id": self.user_id,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }


class Agent:
    """
    Autonomous conversational agent.

    Instantiate with a profile-supplied config dict:
        agent = Agent(config={...}, client=ClaudeClient(...))
    """

    def __init__(
        self,
        config: dict,
        client: ClaudeClient,
        memory: Optional[MemorySystem] = None,
        tools: Optional[ToolRegistry] = None,
    ):
        self.config = config
        self.client = client
        self.memory = memory or MemorySystem(max_history=config.get("memory_size", 50))
        self.tools = tools or ToolRegistry()
        self.name = config.get("agent_name", "Aspasia")
        self.model = config.get("model", "claude-3-5-sonnet-20241022")
        self.max_tokens = config.get("max_tokens", 2048)
        self.temperature = config.get("temperature", 0.7)
        self.system_prompt = config.get("system_prompt", self._default_system_prompt())
        logger.info(f"Agent '{self.name}' ready (model={self.model})")

    def _default_system_prompt(self) -> str:
        return (
            f"You are {self.name}, an autonomous AI assistant. "
            "Be helpful, direct, and honest. "
            "You have memory of the current conversation."
        )

    # ── Public API ───────────────────────────────────────────────────────────

    async def process_message(
        self,
        user_id: str,
        message: str,
        context: Optional[dict] = None,
    ) -> AgentResponse:
        """Main entry point for all adapters."""
        logger.info(f"[{self.name}] msg from {user_id}: {message[:60]}")
        try:
            self.memory.add_message(user_id, "user", message, metadata=context or {})

            history = self.memory.get_conversation(user_id)
            user_ctx = self.memory.get_user_context(user_id)

            system = self._build_system_prompt(user_ctx)
            messages = [{"role": m["role"], "content": m["content"]} for m in history]

            reply = await self.client.chat(
                messages=messages,
                model=self.model,
                system=system,
                max_tokens=self.max_tokens,
                tools=self.tools.list_for_claude(),
                temperature=self.temperature,
            )

            self.memory.add_message(user_id, "assistant", reply, metadata={"source": "claude"})
            return AgentResponse(text=reply, user_id=user_id, metadata={"ctx": user_ctx})

        except Exception as e:
            logger.error(f"process_message error: {e}", exc_info=True)
            return AgentResponse(
                text=f"Ocorreu um erro ao processar a tua mensagem: {e}",
                user_id=user_id,
                metadata={"error": True},
            )

    def clear_history(self, user_id: str) -> None:
        self.memory.clear_user_history(user_id)

    def set_preference(self, user_id: str, key: str, value: Any) -> None:
        self.memory.set_preference(user_id, key, value)

    def get_context(self, user_id: str) -> dict:
        return self.memory.get_user_context(user_id)

    async def health_check(self) -> dict:
        result = {"agent": "healthy", "memory": "healthy", "claude": "unknown"}
        try:
            await self.client.health_check()
            result["claude"] = "healthy"
        except Exception as e:
            result["claude"] = f"unhealthy: {e}"
        return result

    def stats(self) -> dict:
        return {
            "agent_name": self.name,
            "model": self.model,
            "memory": self.memory.stats(),
            "tools": len(self.tools.list_all()),
            "timestamp": datetime.now().isoformat(),
        }

    # ── Internal ─────────────────────────────────────────────────────────────

    def _build_system_prompt(self, user_ctx: dict) -> str:
        prompt = self.system_prompt
        if user_ctx.get("preferences"):
            prompt += f"\n\nUser preferences: {user_ctx['preferences']}"
        if user_ctx.get("facts"):
            prompt += f"\n\nKnown facts: {user_ctx['facts']}"
        return prompt
