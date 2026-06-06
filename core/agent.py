"""
Core Agent — orchestrates Claude, memory, and tools.
Implements the full Anthropic tool-use loop:
  1. Send messages → Claude may reply with tool_use blocks
  2. Execute each tool locally
  3. Send tool_result blocks back → Claude produces final text
No imports from adapters/ or profiles/.
"""

import json
import logging
from datetime import datetime
from typing import Any, Optional

from .llm_client import LLMClient
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
        agent = Agent(config={...}, client=make_client("groq", ...))
    """

    def __init__(
        self,
        config: dict,
        client: LLMClient,
        memory: Optional[MemorySystem] = None,
        tools: Optional[ToolRegistry] = None,
    ):
        self.config = config
        self.client = client
        self.memory = memory or MemorySystem(max_history=config.get("memory_size", 50))
        self.tools = tools or ToolRegistry()
        self.name = config.get("agent_name", "HiveSec Sentinel")
        self.model = config.get("model", "llama-3.3-70b-versatile")
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
        """Main entry point for all adapters. Runs the full tool-use loop."""
        logger.info(f"[{self.name}] msg from {user_id}: {message[:80]}")
        try:
            self.memory.add_message(user_id, "user", message, metadata=context or {})
            history = self._build_messages(user_id)
            system = self._build_system_prompt(self.memory.get_user_context(user_id))
            tool_defs = self.tools.list_for_claude()

            reply = await self._run_tool_loop(history, system, tool_defs)

            self.memory.add_message(user_id, "assistant", reply, metadata={"source": "claude"})
            return AgentResponse(text=reply, user_id=user_id)

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
        result = {"agent": "healthy", "memory": "healthy", "llm": "unknown"}
        try:
            await self.client.health_check()
            result["llm"] = "healthy"
        except Exception as e:
            result["llm"] = f"unhealthy: {e}"
        return result

    def stats(self) -> dict:
        return {
            "agent_name": self.name,
            "model": self.model,
            "memory": self.memory.stats(),
            "tools": len(self.tools.list_all()),
            "timestamp": datetime.now().isoformat(),
        }

    # ── Tool-use loop ────────────────────────────────────────────────────────

    async def _run_tool_loop(
        self,
        messages: list[dict],
        system: str,
        tool_defs: list[dict],
        max_rounds: int = 5,
    ) -> str:
        """
        Runs the Anthropic tool-use agentic loop:
        → send messages
        → if Claude calls tools: execute, append results, repeat
        → when Claude sends a text-only response: return it
        """
        working_messages = list(messages)

        for round_n in range(max_rounds):
            raw = await self.client.chat_raw(
                messages=working_messages,
                model=self.model,
                system=system,
                max_tokens=self.max_tokens,
                tools=tool_defs if tool_defs else None,
                temperature=self.temperature,
            )

            # Collect text and tool_use blocks
            text_parts: list[str] = []
            tool_calls: list[dict] = []
            for block in raw:
                if block.get("type") == "text":
                    text_parts.append(block["text"])
                elif block.get("type") == "tool_use":
                    tool_calls.append(block)

            if not tool_calls:
                # No tools called — final text response
                return "\n".join(text_parts).strip()

            # Append assistant turn (all blocks) to working messages
            working_messages.append({"role": "assistant", "content": raw})

            # Execute each tool and build tool_result content
            tool_results: list[dict] = []
            for tc in tool_calls:
                tool_name = tc["name"]
                tool_input = tc.get("input") or {}
                logger.info(f"Tool call: {tool_name}({tool_input})")
                result = self.tools.execute(tool_name, **tool_input)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tc["id"],
                    "content": json.dumps(result),
                })

            working_messages.append({"role": "user", "content": tool_results})

        logger.warning("Tool loop hit max_rounds — returning partial text")
        return "\n".join(text_parts).strip() or "Não foi possível completar o pedido."

    # ── Internal helpers ─────────────────────────────────────────────────────

    def _build_messages(self, user_id: str) -> list[dict]:
        history = self.memory.get_conversation(user_id)
        return [{"role": m["role"], "content": m["content"]} for m in history]

    def _build_system_prompt(self, user_ctx: dict) -> str:
        prompt = self.system_prompt
        if user_ctx.get("preferences"):
            prompt += f"\n\nUser preferences: {user_ctx['preferences']}"
        if user_ctx.get("facts"):
            prompt += f"\n\nKnown facts: {user_ctx['facts']}"
        return prompt
