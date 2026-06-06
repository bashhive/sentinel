"""
Redis-backed session store.
Drop-in replacement for MemorySystem — same public interface.

Usage in main.py:
    from core.session_redis import RedisMemorySystem
    memory = RedisMemorySystem(redis_url=cfg.redis_url)
    agent  = Agent(config=..., client=..., memory=memory)

Requires: redis>=5.0  (already in pyproject.toml optional-deps if needed)
Add to pyproject.toml dependencies when enabling:
    "redis>=5.0",
"""

import json
import logging
from datetime import datetime
from typing import Any, Optional

logger = logging.getLogger(__name__)

try:
    import redis.asyncio as aioredis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("redis package not installed — RedisMemorySystem unavailable")


class RedisMemorySystem:
    """
    Per-user conversation history stored in Redis.
    Keys: hivesec:{user_id}:history  (JSON list)
          hivesec:{user_id}:meta     (JSON dict: preferences, facts)

    TTL: 24h by default (configurable). Sessions expire after inactivity.
    """

    PREFIX = "hivesec"
    DEFAULT_TTL = 86_400  # 24 hours in seconds

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379/0",
        max_history: int = 50,
        ttl: int = DEFAULT_TTL,
    ):
        if not REDIS_AVAILABLE:
            raise RuntimeError("Install redis: pip install redis>=5.0")
        self.max_history = max_history
        self.ttl = ttl
        self._redis = aioredis.from_url(redis_url, decode_responses=True)

    # ── Internal key helpers ─────────────────────────────────────────────────

    def _hkey(self, user_id: str) -> str:
        return f"{self.PREFIX}:{user_id}:history"

    def _mkey(self, user_id: str) -> str:
        return f"{self.PREFIX}:{user_id}:meta"

    # ── Core access (async) ──────────────────────────────────────────────────

    async def add_message_async(
        self, user_id: str, role: str, content: str, metadata: dict = None
    ) -> None:
        key = self._hkey(user_id)
        msg = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {},
        }
        pipe = self._redis.pipeline()
        pipe.rpush(key, json.dumps(msg))
        pipe.ltrim(key, -self.max_history, -1)  # keep last N
        pipe.expire(key, self.ttl)
        await pipe.execute()

    async def get_conversation_async(
        self, user_id: str, limit: int = 20
    ) -> list[dict]:
        key = self._hkey(user_id)
        raw = await self._redis.lrange(key, -limit, -1)
        return [json.loads(m) for m in raw]

    async def clear_user_history_async(self, user_id: str) -> None:
        await self._redis.delete(self._hkey(user_id))

    # ── Sync wrappers (for MemorySystem compatibility) ────────────────────────
    # Agent calls these synchronously from coroutine context — run_until_complete
    # is not available inside async, so we maintain async methods and let
    # Agent call the async versions directly.
    # Override the MemorySystem parent class's sync interface here:

    def add_message(self, user_id: str, role: str, content: str, metadata: dict = None):
        """Sync shim — only safe to call from non-async context (e.g. tests)."""
        import asyncio
        asyncio.get_event_loop().run_until_complete(
            self.add_message_async(user_id, role, content, metadata)
        )

    def get_conversation(self, user_id: str, limit: int = 20) -> list[dict]:
        import asyncio
        return asyncio.get_event_loop().run_until_complete(
            self.get_conversation_async(user_id, limit)
        )

    def clear_user_history(self, user_id: str) -> None:
        import asyncio
        asyncio.get_event_loop().run_until_complete(
            self.clear_user_history_async(user_id)
        )

    # ── Preferences & facts (via meta hash) ──────────────────────────────────

    async def _get_meta(self, user_id: str) -> dict:
        raw = await self._redis.get(self._mkey(user_id))
        return json.loads(raw) if raw else {"preferences": {}, "facts": {}}

    async def _save_meta(self, user_id: str, meta: dict) -> None:
        await self._redis.set(self._mkey(user_id), json.dumps(meta), ex=self.ttl)

    def set_preference(self, user_id: str, key: str, value: Any) -> None:
        import asyncio
        async def _set():
            meta = await self._get_meta(user_id)
            meta["preferences"][key] = value
            await self._save_meta(user_id, meta)
        asyncio.get_event_loop().run_until_complete(_set())

    def get_preference(self, user_id: str, key: str, default: Any = None) -> Any:
        import asyncio
        async def _get():
            meta = await self._get_meta(user_id)
            return meta["preferences"].get(key, default)
        return asyncio.get_event_loop().run_until_complete(_get())

    def store_fact(self, user_id: str, key: str, fact: str) -> None:
        import asyncio
        async def _store():
            meta = await self._get_meta(user_id)
            meta["facts"][key] = fact
            await self._save_meta(user_id, meta)
        asyncio.get_event_loop().run_until_complete(_store())

    def get_user_context(self, user_id: str) -> dict:
        import asyncio
        async def _ctx():
            meta = await self._get_meta(user_id)
            history = await self.get_conversation_async(user_id, limit=1)
            return {
                "user_id": user_id,
                "last_interaction": history[-1]["timestamp"] if history else None,
                "message_count": await self._redis.llen(self._hkey(user_id)),
                "preferences": meta["preferences"],
                "facts": meta["facts"],
            }
        return asyncio.get_event_loop().run_until_complete(_ctx())

    def stats(self) -> dict:
        """Approximate stats — scans keys with PREFIX pattern."""
        import asyncio
        async def _stats():
            keys = await self._redis.keys(f"{self.PREFIX}:*:history")
            total_users = len(keys)
            counts = await asyncio.gather(*[self._redis.llen(k) for k in keys])
            total_messages = sum(counts)
            return {
                "total_users": total_users,
                "total_messages": total_messages,
                "avg_messages_per_user": total_messages // total_users if total_users else 0,
            }
        return asyncio.get_event_loop().run_until_complete(_stats())

    async def health_check(self) -> bool:
        await self._redis.ping()
        return True
