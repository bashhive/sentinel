"""
Core agent logic for Aspasia.

Manages conversation flow, integrates Claude AI, and orchestrates responses.
"""

import asyncio
from typing import Optional, Any
from datetime import datetime
import logging

from aspasia.agent.memory import MemorySystem
from aspasia.agent.prompts import get_system_prompt, format_conversation_context
from aspasia.agent.tools import ToolRegistry
from aspasia.integrations.claude_api import ClaudeAPI
from aspasia.config import Config


logger = logging.getLogger(__name__)


class AgentResponse:
    """Response from the agent."""

    def __init__(
        self,
        text: str,
        user_id: str,
        timestamp: datetime = None,
        metadata: dict = None,
    ):
        self.text = text
        self.user_id = user_id
        self.timestamp = timestamp or datetime.now()
        self.metadata = metadata or {}

    def to_dict(self) -> dict:
        """Convert response to dictionary."""
        return {
            "text": self.text,
            "user_id": self.user_id,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }


class Agent:
    """Core autonomous agent implementation."""

    def __init__(
        self,
        config: Config,
        claude_client: ClaudeAPI,
        memory_system: Optional[MemorySystem] = None,
        tool_registry: Optional[ToolRegistry] = None,
    ):
        """
        Initialize the agent.

        Args:
            config: Configuration instance
            claude_client: Claude API client
            memory_system: Optional memory system (creates default if not provided)
            tool_registry: Optional tool registry (creates default if not provided)
        """
        self.config = config
        self.claude_client = claude_client
        self.memory = memory_system or MemorySystem(max_history=config.agent_memory_size)
        self.tools = tool_registry or ToolRegistry()
        self.system_prompt = get_system_prompt(config.agent_name)

        logger.info(f"Agent initialized: {config.agent_name}")

    async def process_message(
        self,
        user_id: str,
        message: str,
        context: Optional[dict] = None,
    ) -> AgentResponse:
        """
        Process a message from a user.

        Args:
            user_id: User identifier
            message: User's message
            context: Additional context (platform, user_name, etc.)

        Returns:
            AgentResponse with agent's reply
        """
        logger.info(f"Processing message from {user_id}", extra={"user_id": user_id})

        try:
            # Add user message to memory
            self.memory.add_message(
                user_id=user_id,
                role="user",
                content=message,
                metadata=context or {},
            )

            # Build conversation context
            conversation = self.memory.get_conversation(user_id)
            user_context = self.memory.get_user_context(user_id)

            # Get response from Claude
            response_text = await self._get_claude_response(
                user_id=user_id,
                message=message,
                conversation_history=conversation,
                user_context=user_context,
            )

            # Add assistant response to memory
            self.memory.add_message(
                user_id=user_id,
                role="assistant",
                content=response_text,
                metadata={"source": "claude"},
            )

            response = AgentResponse(
                text=response_text,
                user_id=user_id,
                metadata={"context": user_context},
            )

            logger.info(f"Response sent to {user_id}")
            return response

        except Exception as e:
            logger.error(f"Error processing message: {str(e)}", exc_info=True)
            error_response = AgentResponse(
                text=f"I encountered an error processing your message: {str(e)}",
                user_id=user_id,
                metadata={"error": True},
            )
            return error_response

    async def _get_claude_response(
        self,
        user_id: str,
        message: str,
        conversation_history: list[dict],
        user_context: dict,
    ) -> str:
        """
        Get a response from Claude API.

        Args:
            user_id: User ID
            message: User's message
            conversation_history: List of previous messages
            user_context: Context about the user

        Returns:
            Response text from Claude
        """
        # Format messages for Claude API
        messages = [
            {"role": msg["role"], "content": msg["content"]}
            for msg in conversation_history
        ]

        # Build system prompt with context
        system_prompt = self.system_prompt
        if user_context.get("preferences"):
            system_prompt += f"\n\nUser Preferences: {user_context['preferences']}"
        if user_context.get("facts"):
            system_prompt += f"\n\nKnown Facts: {user_context['facts']}"

        # Call Claude
        response = await self.claude_client.chat(
            messages=messages,
            system=system_prompt,
            model=self.config.claude_model,
            max_tokens=self.config.claude_max_tokens,
            tools=self.tools.list_for_claude(),
        )

        return response

    def set_user_preference(self, user_id: str, key: str, value: Any) -> None:
        """Set a user preference."""
        self.memory.set_user_preference(user_id, key, value)
        logger.debug(f"Set preference {key} for user {user_id}")

    def store_user_fact(self, user_id: str, fact: str) -> None:
        """Store a fact about a user."""
        self.memory.store_user_fact(user_id, "auto_fact", fact)

    def get_user_context(self, user_id: str) -> dict:
        """Get full context for a user."""
        return self.memory.get_user_context(user_id)

    def clear_user_history(self, user_id: str) -> None:
        """Clear conversation history for a user."""
        self.memory.clear_user_history(user_id)
        logger.info(f"Cleared history for user {user_id}")

    async def health_check(self) -> dict:
        """Perform health check on agent and dependencies."""
        checks = {
            "agent": "healthy",
            "memory": "healthy",
            "claude": "unknown",
            "timestamp": datetime.now().isoformat(),
        }

        try:
            # Check Claude connectivity
            await self.claude_client.health_check()
            checks["claude"] = "healthy"
        except Exception as e:
            checks["claude"] = f"unhealthy: {str(e)}"

        return checks

    def get_stats(self) -> dict:
        """Get agent statistics."""
        memory_stats = self.memory.get_stats()
        return {
            "agent_name": self.config.agent_name,
            "model": self.config.claude_model,
            "timestamp": datetime.now().isoformat(),
            "memory": memory_stats,
            "tools_available": len(self.tools.list_all()),
        }
