"""
Memory system for Aspasia agent.

Handles conversation history, user preferences, and learned patterns.
"""

from typing import Optional, Any
from datetime import datetime
from dataclasses import dataclass, field, asdict
import json
from pathlib import Path


@dataclass
class Message:
    """A single message in conversation history."""

    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        return data


@dataclass
class UserMemory:
    """Memory about a specific user."""

    user_id: str
    created_at: datetime = field(default_factory=datetime.now)
    last_interaction: Optional[datetime] = None
    conversation_history: list[Message] = field(default_factory=list)
    preferences: dict[str, Any] = field(default_factory=dict)
    facts: dict[str, str] = field(default_factory=dict)  # Learned facts about user

    def add_message(self, role: str, content: str, metadata: dict = None) -> None:
        """Add a message to history."""
        self.conversation_history.append(
            Message(role=role, content=content, metadata=metadata or {})
        )
        self.last_interaction = datetime.now()

    def get_recent_messages(self, limit: int = 10) -> list[dict]:
        """Get recent messages as dicts."""
        messages = self.conversation_history[-limit:]
        return [msg.to_dict() for msg in messages]

    def set_preference(self, key: str, value: Any) -> None:
        """Store a user preference."""
        self.preferences[key] = value

    def get_preference(self, key: str, default: Any = None) -> Any:
        """Get a user preference."""
        return self.preferences.get(key, default)

    def store_fact(self, key: str, fact: str) -> None:
        """Store a fact about the user."""
        self.facts[key] = fact

    def get_fact(self, key: str) -> Optional[str]:
        """Retrieve a stored fact."""
        return self.facts.get(key)


class MemorySystem:
    """In-memory storage system for user conversations and context."""

    def __init__(self, max_history: int = 100):
        """
        Initialize memory system.

        Args:
            max_history: Maximum messages to keep per user
        """
        self.max_history = max_history
        self.users: dict[str, UserMemory] = {}

    def get_or_create_user(self, user_id: str) -> UserMemory:
        """Get or create user memory."""
        if user_id not in self.users:
            self.users[user_id] = UserMemory(user_id=user_id)
        return self.users[user_id]

    def add_message(
        self, user_id: str, role: str, content: str, metadata: dict = None
    ) -> None:
        """Add a message to user's conversation history."""
        user = self.get_or_create_user(user_id)
        user.add_message(role, content, metadata)

        # Trim history if too long
        if len(user.conversation_history) > self.max_history:
            user.conversation_history = user.conversation_history[-self.max_history :]

    def get_conversation(self, user_id: str, limit: int = 10) -> list[dict]:
        """Get conversation history for a user."""
        user = self.get_or_create_user(user_id)
        return user.get_recent_messages(limit)

    def set_user_preference(self, user_id: str, key: str, value: Any) -> None:
        """Set a user preference."""
        user = self.get_or_create_user(user_id)
        user.set_preference(key, value)

    def get_user_preference(self, user_id: str, key: str, default: Any = None) -> Any:
        """Get a user preference."""
        user = self.get_or_create_user(user_id)
        return user.get_preference(key, default)

    def store_user_fact(self, user_id: str, key: str, fact: str) -> None:
        """Store a fact about a user."""
        user = self.get_or_create_user(user_id)
        user.store_fact(key, fact)

    def get_user_fact(self, user_id: str, key: str) -> Optional[str]:
        """Retrieve a fact about a user."""
        user = self.get_or_create_user(user_id)
        return user.get_fact(key)

    def get_user_context(self, user_id: str) -> dict[str, Any]:
        """Get full context for a user."""
        user = self.get_or_create_user(user_id)
        return {
            "user_id": user_id,
            "created_at": user.created_at.isoformat(),
            "last_interaction": user.last_interaction.isoformat()
            if user.last_interaction
            else None,
            "message_count": len(user.conversation_history),
            "preferences": user.preferences,
            "facts": user.facts,
        }

    def clear_user_history(self, user_id: str) -> None:
        """Clear conversation history for a user."""
        if user_id in self.users:
            self.users[user_id].conversation_history = []

    def export_user_data(self, user_id: str) -> dict:
        """Export all data for a user."""
        user = self.get_or_create_user(user_id)
        return {
            "user_id": user.user_id,
            "created_at": user.created_at.isoformat(),
            "last_interaction": user.last_interaction.isoformat()
            if user.last_interaction
            else None,
            "preferences": user.preferences,
            "facts": user.facts,
            "conversation_history": user.get_recent_messages(limit=None),
        }

    def import_user_data(self, data: dict) -> None:
        """Import user data."""
        user_id = data.get("user_id")
        if not user_id:
            raise ValueError("user_id required")

        user = self.get_or_create_user(user_id)
        user.preferences = data.get("preferences", {})
        user.facts = data.get("facts", {})

        # Reload conversation history
        for msg_data in data.get("conversation_history", []):
            user.conversation_history.append(
                Message(
                    role=msg_data["role"],
                    content=msg_data["content"],
                    timestamp=datetime.fromisoformat(msg_data["timestamp"]),
                    metadata=msg_data.get("metadata", {}),
                )
            )

    def get_stats(self) -> dict:
        """Get memory system statistics."""
        total_users = len(self.users)
        total_messages = sum(
            len(user.conversation_history) for user in self.users.values()
        )
        return {
            "total_users": total_users,
            "total_messages": total_messages,
            "avg_messages_per_user": (
                total_messages // total_users if total_users > 0 else 0
            ),
        }
