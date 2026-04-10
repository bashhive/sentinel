"""
Integration tests — web adapter (FastAPI).
Uses httpx TestClient — no real server or API calls.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient

from core.agent import Agent, AgentResponse
from adapters.web.app import create_app


def make_agent(reply: str = "Test reply") -> Agent:
    """Build an Agent with a mocked ClaudeClient."""
    mock_client = MagicMock()
    mock_client.chat = AsyncMock(return_value=reply)
    mock_client.health_check = AsyncMock(return_value=True)
    return Agent(
        config={
            "agent_name": "TestBot",
            "model": "claude-3-5-sonnet-20241022",
            "max_tokens": 100,
            "temperature": 0.5,
            "system_prompt": "You are a test bot.",
        },
        client=mock_client,
    )


# ── Health / Status ───────────────────────────────────────────────────────────

class TestHealthEndpoints:
    def setup_method(self):
        self.app = create_app(agent=make_agent(), cors_origins=["*"])
        self.client = TestClient(self.app)

    def test_root(self):
        r = self.client.get("/")
        assert r.status_code == 200
        assert r.json()["status"] == "running"

    def test_health(self):
        r = self.client.get("/api/health")
        assert r.status_code == 200
        data = r.json()
        assert data["agent"] == "healthy"
        assert data["claude"] == "healthy"

    def test_status(self):
        r = self.client.get("/api/status")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "online"
        assert data["agent_name"] == "TestBot"


# ── Chat endpoint — BASH_site widget compatibility ────────────────────────────

class TestChatEndpoint:
    """
    BASH_site sends:  POST /api/chat  { message: str, language?: str }
    BASH_site reads:  data.message || data.reply || data.response
    Our adapter returns: { message: str, session_id: str }  ← .message ✓
    """

    def setup_method(self):
        self.app = create_app(agent=make_agent("Olá!"), cors_origins=["https://bash.pt"])
        self.client = TestClient(self.app)

    def test_basic_chat(self):
        r = self.client.post("/api/chat", json={"message": "hello"})
        assert r.status_code == 200
        data = r.json()
        assert "message" in data          # widget reads data.message
        assert data["message"] == "Olá!"
        assert "session_id" in data

    def test_session_id_preserved(self):
        r = self.client.post("/api/chat", json={"message": "hi", "session_id": "user-42"})
        assert r.json()["session_id"] == "user-42"

    def test_default_session_id(self):
        r = self.client.post("/api/chat", json={"message": "hi"})
        assert r.json()["session_id"] == "default"

    def test_empty_message_rejected(self):
        # pydantic will reject missing required field
        r = self.client.post("/api/chat", json={})
        assert r.status_code == 422

    def test_lang_prefix_in_message(self):
        """Widget prepends '[Responde em Português de Portugal] ' — must pass through."""
        r = self.client.post("/api/chat", json={
            "message": "[Responde em Português de Portugal] Olá",
            "session_id": "pt-user"
        })
        assert r.status_code == 200
        assert "message" in r.json()


# ── History & Reset ───────────────────────────────────────────────────────────

class TestSessionManagement:
    def setup_method(self):
        self.agent = make_agent("pong")
        self.app = create_app(agent=self.agent, cors_origins=["*"])
        self.client = TestClient(self.app)

    def test_history_empty_initially(self):
        r = self.client.get("/api/history?session_id=fresh")
        assert r.status_code == 200
        assert r.json()["history"] == []

    def test_history_after_chat(self):
        self.client.post("/api/chat", json={"message": "ping", "session_id": "s1"})
        r = self.client.get("/api/history?session_id=s1")
        assert len(r.json()["history"]) == 2  # user + assistant

    def test_reset_clears_history(self):
        self.client.post("/api/chat", json={"message": "ping", "session_id": "s2"})
        self.client.post("/api/reset", json={"message": "", "session_id": "s2"})
        r = self.client.get("/api/history?session_id=s2")
        assert r.json()["history"] == []


# ── API key guard ─────────────────────────────────────────────────────────────

class TestApiKeyGuard:
    def setup_method(self):
        self.app = create_app(
            agent=make_agent(),
            cors_origins=["*"],
            api_key="secret-key",
        )
        self.client = TestClient(self.app)

    def test_no_key_rejected(self):
        r = self.client.post("/api/chat", json={"message": "hi"})
        assert r.status_code == 403

    def test_wrong_key_rejected(self):
        r = self.client.post("/api/chat", json={"message": "hi"},
                             headers={"X-API-Key": "wrong"})
        assert r.status_code == 403

    def test_correct_key_accepted(self):
        r = self.client.post("/api/chat", json={"message": "hi"},
                             headers={"X-API-Key": "secret-key"})
        assert r.status_code == 200
