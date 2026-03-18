"""
Tool definitions and handlers for agent use.

This module defines tools the agent can use to interact with the world.
"""

from typing import Any, Callable, Optional
from dataclasses import dataclass
from enum import Enum


class ToolType(Enum):
    """Types of tools available to the agent."""

    INFORMATION = "information"  # Tools for gathering information
    ACTION = "action"  # Tools for taking actions
    INTEGRATION = "integration"  # Integration with external services


@dataclass
class Tool:
    """Definition of a tool the agent can use."""

    name: str
    description: str
    parameters: dict[str, Any]
    tool_type: ToolType
    handler: Optional[Callable] = None
    requires_approval: bool = False

    def to_dict(self) -> dict:
        """Convert tool to dictionary for Claude API."""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": {
                "type": "object",
                "properties": self.parameters,
                "required": list(self.parameters.keys()),
            },
        }


class ToolRegistry:
    """Registry for available tools."""

    def __init__(self):
        self.tools: dict[str, Tool] = {}
        self._init_default_tools()

    def _init_default_tools(self) -> None:
        """Initialize default tools."""

        # Search tool
        self.register(
            Tool(
                name="search_information",
                description="Search for information on a topic",
                parameters={
                    "query": {
                        "type": "string",
                        "description": "Search query",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum results to return",
                        "default": 5,
                    },
                },
                tool_type=ToolType.INFORMATION,
            )
        )

        # Memory tool
        self.register(
            Tool(
                name="recall_memory",
                description="Recall stored memories or facts about a user",
                parameters={
                    "user_id": {
                        "type": "string",
                        "description": "User ID to recall memories for",
                    },
                    "query": {
                        "type": "string",
                        "description": "What to remember (optional)",
                    },
                },
                tool_type=ToolType.INFORMATION,
            )
        )

        # Store memory tool
        self.register(
            Tool(
                name="store_memory",
                description="Store a memory or fact for later recall",
                parameters={
                    "user_id": {
                        "type": "string",
                        "description": "User ID",
                    },
                    "content": {
                        "type": "string",
                        "description": "Memory content",
                    },
                    "category": {
                        "type": "string",
                        "description": "Category (preference, fact, etc.)",
                    },
                },
                tool_type=ToolType.INFORMATION,
            )
        )

        # Notification tool
        self.register(
            Tool(
                name="send_notification",
                description="Send a notification to user (requires approval)",
                parameters={
                    "user_id": {
                        "type": "string",
                        "description": "User ID",
                    },
                    "message": {
                        "type": "string",
                        "description": "Notification message",
                    },
                    "priority": {
                        "type": "string",
                        "enum": ["low", "medium", "high"],
                        "description": "Priority level",
                    },
                },
                tool_type=ToolType.ACTION,
                requires_approval=True,
            )
        )

        # Schedule task tool
        self.register(
            Tool(
                name="schedule_task",
                description="Schedule a task for later (requires approval)",
                parameters={
                    "task": {
                        "type": "string",
                        "description": "Task description",
                    },
                    "scheduled_time": {
                        "type": "string",
                        "description": "ISO 8601 datetime (e.g., 2024-01-15T10:30:00)",
                    },
                    "user_id": {
                        "type": "string",
                        "description": "User ID",
                    },
                },
                tool_type=ToolType.ACTION,
                requires_approval=True,
            )
        )

    def register(self, tool: Tool) -> None:
        """Register a new tool."""
        self.tools[tool.name] = tool

    def get(self, name: str) -> Optional[Tool]:
        """Get a tool by name."""
        return self.tools.get(name)

    def list_all(self) -> list[Tool]:
        """List all registered tools."""
        return list(self.tools.values())

    def list_for_claude(self) -> list[dict]:
        """Get tools formatted for Claude API."""
        return [tool.to_dict() for tool in self.tools.values()]

    def get_by_type(self, tool_type: ToolType) -> list[Tool]:
        """Get tools by type."""
        return [tool for tool in self.tools.values() if tool.tool_type == tool_type]
