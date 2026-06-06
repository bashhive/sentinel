"""
Unit tests — core (no network, no Claude API calls).
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from core.session import MemorySystem, Message
from core.tools import ToolRegistry, ToolType
from core.agent import Agent, AgentResponse


# ── MemorySystem ──────────────────────────────────────────────────────────────

class TestMemorySystem:
    def setup_method(self):
        self.mem = MemorySystem(max_history=5)

    def test_add_and_retrieve(self):
        self.mem.add_message("u1", "user", "hello")
        self.mem.add_message("u1", "assistant", "hi")
        history = self.mem.get_conversation("u1")
        assert len(history) == 2
        assert history[0]["role"] == "user"
        assert history[1]["role"] == "assistant"

    def test_max_history_trim(self):
        for i in range(10):
            self.mem.add_message("u1", "user", f"msg {i}")
        history = self.mem.get_conversation("u1", limit=100)
        assert len(history) == 5

    def test_clear_history(self):
        self.mem.add_message("u1", "user", "hello")
        self.mem.clear_user_history("u1")
        assert self.mem.get_conversation("u1") == []

    def test_preferences(self):
        self.mem.set_preference("u1", "lang", "pt")
        assert self.mem.get_preference("u1", "lang") == "pt"
        assert self.mem.get_preference("u1", "missing", "default") == "default"

    def test_facts(self):
        self.mem.store_fact("u1", "name", "Raf")
        ctx = self.mem.get_user_context("u1")
        assert ctx["facts"]["name"] == "Raf"

    def test_stats(self):
        self.mem.add_message("u1", "user", "a")
        self.mem.add_message("u2", "user", "b")
        stats = self.mem.stats()
        assert stats["total_users"] == 2
        assert stats["total_messages"] == 2

    def test_separate_users(self):
        self.mem.add_message("u1", "user", "for u1")
        self.mem.add_message("u2", "user", "for u2")
        assert len(self.mem.get_conversation("u1")) == 1
        assert len(self.mem.get_conversation("u2")) == 1


# ── ToolRegistry ──────────────────────────────────────────────────────────────

class TestToolRegistry:
    def setup_method(self):
        self.reg = ToolRegistry()

    def test_default_tools_registered(self):
        names = [t.name for t in self.reg.list_all()]
        assert "get_time" in names
        assert "calculate" in names

    def test_get_time(self):
        result = self.reg.execute("get_time")
        assert "timestamp" in result
        assert "formatted" in result

    def test_calculate_valid(self):
        result = self.reg.execute("calculate", expression="2 + 2 * 3")
        assert result["result"] == 8

    def test_calculate_safe_eval(self):
        result = self.reg.execute("calculate", expression="__import__('os').getcwd()")
        assert "error" in result

    def test_calculate_power(self):
        result = self.reg.execute("calculate", expression="2 ** 10")
        assert result["result"] == 1024

    def test_unknown_tool(self):
        result = self.reg.execute("nonexistent")
        assert "error" in result

    def test_claude_format(self):
        tools = self.reg.list_for_claude()
        assert all("name" in t and "input_schema" in t for t in tools)

    def test_register_custom(self):
        from core.tools import Tool
        def my_handler():
            return {"ok": True}
        self.reg.register(Tool(
            name="custom_tool",
            description="test",
            parameters={},
            tool_type=ToolType.INFORMATION,
            handler=my_handler,
        ))
        result = self.reg.execute("custom_tool")
        assert result["ok"] is True


# ── Agent ─────────────────────────────────────────────────────────────────────

class TestAgent:
    def setup_method(self):
        self.mock_client = MagicMock()
        # chat_raw returns text blocks (no tool calls in unit tests)
        self.mock_client.chat_raw = AsyncMock(
            return_value=[{"type": "text", "text": "Mocked reply"}]
        )
        self.mock_client.health_check = AsyncMock(return_value=True)

        self.agent = Agent(
            config={
                "agent_name": "TestBot",
                "model": "llama-3.3-70b-versatile",
                "max_tokens": 100,
                "temperature": 0.5,
                "system_prompt": "You are a test bot.",
            },
            client=self.mock_client,
        )

    @pytest.mark.asyncio
    async def test_process_message_returns_response(self):
        resp = await self.agent.process_message("u1", "hello")
        assert isinstance(resp, AgentResponse)
        assert resp.text == "Mocked reply"
        assert resp.user_id == "u1"

    @pytest.mark.asyncio
    async def test_conversation_persists(self):
        await self.agent.process_message("u1", "first")
        await self.agent.process_message("u1", "second")
        history = self.agent.memory.get_conversation("u1")
        assert len(history) == 4  # 2 user + 2 assistant

    @pytest.mark.asyncio
    async def test_clear_history(self):
        await self.agent.process_message("u1", "hello")
        self.agent.clear_history("u1")
        assert self.agent.memory.get_conversation("u1") == []

    @pytest.mark.asyncio
    async def test_health_check(self):
        health = await self.agent.health_check()
        assert health["agent"] == "healthy"
        assert health["llm"] == "healthy"

    @pytest.mark.asyncio
    async def test_error_handling(self):
        self.mock_client.chat_raw = AsyncMock(side_effect=Exception("API down"))
        resp = await self.agent.process_message("u1", "hello")
        assert resp.metadata.get("error") is True

    def test_stats(self):
        stats = self.agent.stats()
        assert stats["agent_name"] == "TestBot"
        assert "memory" in stats
        assert "tools" in stats

    @pytest.mark.asyncio
    async def test_tool_loop_executes_tool(self):
        """Agent should execute tool and send result back to Claude."""
        call_count = 0

        async def mock_raw(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # First call: Claude requests a tool
                return [{"type": "tool_use", "id": "t1", "name": "get_time", "input": {}}]
            else:
                # Second call: Claude responds after seeing tool result
                return [{"type": "text", "text": "The time is now."}]

        self.mock_client.chat_raw = mock_raw
        resp = await self.agent.process_message("u1", "what time is it?")
        assert resp.text == "The time is now."
        assert call_count == 2
