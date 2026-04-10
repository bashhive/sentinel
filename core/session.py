"""
Session / memory system — per-user conversation history and context.
In-memory by default; swap backend via subclass.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional


@dataclass
class Message:
    role: str          # "user" | "assistant"
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }


@dataclass
class UserMemory:
    user_id: str
    created_at: datetime = field(default_factory=datetime.now)
    last_interaction: Optional[datetime] = None
    conversation_history: list[Message] = field(default_factory=list)
    preferences: dict[str, Any] = field(default_factory=dict)
    facts: dict[str, str] = field(default_factory=dict)

    def add_message(self, role: str, content: str, metadata: dict = None) -> None:
        self.conversation_history.append(
            Message(role=role, content=content, metadata=metadata or {})
        )
        self.last_interaction = datetime.now()

    def get_recent_messages(self, limit: int = 10) -> list[dict]:
        msgs = self.conversation_history[-limit:] if limit else self.conversation_history
        return [m.to_dict() for m in msgs]


class MemorySystem:
    """
    In-memory session store. Thread-safe for async use within a single process.
    Swap for Redis/SQLite backend by subclassing and overriding store/fetch methods.
    """

    def __init__(self, max_history: int = 50):
        self.max_history = max_history
        self._users: dict[str, UserMemory] = {}

    # ── Core access ─────────────────────────────────────────────────────────

    def _user(self, user_id: str) -> UserMemory:
        if user_id not in self._users:
            self._users[user_id] = UserMemory(user_id=user_id)
        return self._users[user_id]

    def add_message(self, user_id: str, role: str, content: str, metadata: dict = None) -> None:
        u = self._user(user_id)
        u.add_message(role, content, metadata)
        if len(u.conversation_history) > self.max_history:
            u.conversation_history = u.conversation_history[-self.max_history:]

    def get_conversation(self, user_id: str, limit: int = 20) -> list[dict]:
        return self._user(user_id).get_recent_messages(limit)

    def clear_user_history(self, user_id: str) -> None:
        if user_id in self._users:
            self._users[user_id].conversation_history = []

    # ── Preferences & facts ──────────────────────────────────────────────────

    def set_preference(self, user_id: str, key: str, value: Any) -> None:
        self._user(user_id).preferences[key] = value

    def get_preference(self, user_id: str, key: str, default: Any = None) -> Any:
        return self._user(user_id).preferences.get(key, default)

    def store_fact(self, user_id: str, key: str, fact: str) -> None:
        self._user(user_id).facts[key] = fact

    def get_user_context(self, user_id: str) -> dict:
        u = self._user(user_id)
        return {
            "user_id": user_id,
            "created_at": u.created_at.isoformat(),
            "last_interaction": u.last_interaction.isoformat() if u.last_interaction else None,
            "message_count": len(u.conversation_history),
            "preferences": u.preferences,
            "facts": u.facts,
        }

    # ── Stats ────────────────────────────────────────────────────────────────

    def stats(self) -> dict:
        total_users = len(self._users)
        total_msgs = sum(len(u.conversation_history) for u in self._users.values())
        return {
            "total_users": total_users,
            "total_messages": total_msgs,
            "avg_messages_per_user": total_msgs // total_users if total_users else 0,
        }
