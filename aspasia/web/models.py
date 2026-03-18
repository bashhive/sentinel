"""Pydantic models for API requests and responses."""

from typing import Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime


class ChatRequest(BaseModel):
    """Request model for chat endpoint."""

    user_id: str = Field(..., description="User identifier")
    message: str = Field(..., min_length=1, description="User message")
    context: Optional[dict[str, Any]] = Field(
        default=None, description="Additional context"
    )


class ChatResponse(BaseModel):
    """Response model for chat endpoint."""

    text: str = Field(..., description="Response text")
    user_id: str = Field(..., description="User identifier")
    timestamp: str = Field(..., description="ISO 8601 timestamp")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Metadata")


class HistoryResponse(BaseModel):
    """Response model for conversation history."""

    user_id: str = Field(..., description="User identifier")
    messages: list[dict] = Field(..., description="Conversation messages")
    count: int = Field(..., description="Number of messages")


class UserContextResponse(BaseModel):
    """Response model for user context."""

    user_id: str = Field(..., description="User identifier")
    created_at: str = Field(..., description="ISO 8601 creation timestamp")
    last_interaction: Optional[str] = Field(..., description="ISO 8601 last interaction")
    message_count: int = Field(..., description="Total message count")
    preferences: dict[str, Any] = Field(..., description="User preferences")
    facts: dict[str, str] = Field(..., description="Known facts about user")


class HealthResponse(BaseModel):
    """Response model for health check."""

    agent: str = Field(..., description="Agent status")
    memory: str = Field(..., description="Memory system status")
    claude: str = Field(..., description="Claude API status")
    timestamp: str = Field(..., description="ISO 8601 timestamp")


class StatsResponse(BaseModel):
    """Response model for statistics."""

    agent_name: str = Field(..., description="Agent name")
    model: str = Field(..., description="Claude model")
    timestamp: str = Field(..., description="ISO 8601 timestamp")
    memory: dict[str, int] = Field(..., description="Memory statistics")
    tools_available: int = Field(..., description="Number of available tools")


class PreferenceRequest(BaseModel):
    """Request model for setting preferences."""

    key: str = Field(..., description="Preference key")
    value: Any = Field(..., description="Preference value")


class ErrorResponse(BaseModel):
    """Response model for errors."""

    error: str = Field(..., description="Error message")
    timestamp: str = Field(..., description="ISO 8601 timestamp")
    details: Optional[dict[str, Any]] = Field(default=None, description="Error details")
