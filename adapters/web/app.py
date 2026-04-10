"""
Web adapter — FastAPI app.
CORS origins and API key are injected by the profile at startup.
No profile-specific logic lives here.
"""

import logging
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException, Depends, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security.api_key import APIKeyHeader
from pydantic import BaseModel

from core.agent import Agent

logger = logging.getLogger(__name__)

# ── Pydantic models ──────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"

class ChatResponse(BaseModel):
    message: str
    session_id: str

class StatusResponse(BaseModel):
    status: str
    agent_name: str
    model: str
    timestamp: str


# ── Factory ──────────────────────────────────────────────────────────────────

def create_app(
    agent: Agent,
    cors_origins: list[str] = None,
    api_key: Optional[str] = None,
    title: str = "Aspasia API",
) -> FastAPI:
    """
    Build and return a configured FastAPI instance.
    Called by main.py after the profile is resolved.
    """

    app = FastAPI(title=title, version="2.0.0")

    # CORS — profile supplies allowed origins
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins or ["*"],
        allow_credentials=True,
        allow_methods=["POST", "GET"],
        allow_headers=["*"],
    )

    # Optional API-key guard
    api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

    async def verify_key(key: str = Security(api_key_header)):
        if api_key and key != api_key:
            raise HTTPException(status_code=403, detail="Invalid API key")

    # ── Routes ───────────────────────────────────────────────────────────────

    @app.get("/", tags=["Health"])
    async def root():
        return {"name": title, "version": "2.0.0", "status": "running"}

    @app.get("/api/health", tags=["Health"])
    async def health():
        checks = await agent.health_check()
        return {**checks, "timestamp": datetime.now().isoformat()}


    @app.get("/api/status", response_model=StatusResponse, tags=["Status"])
    async def status():
        s = agent.stats()
        return StatusResponse(
            status="online",
            agent_name=s["agent_name"],
            model=s["model"],
            timestamp=s["timestamp"],
        )

    @app.post("/api/chat", response_model=ChatResponse, tags=["Chat"],
              dependencies=[Depends(verify_key)])
    async def chat(req: ChatRequest):
        try:
            resp = await agent.process_message(
                user_id=req.session_id,
                message=req.message,
                context={"platform": "web", "session_id": req.session_id},
            )
            return ChatResponse(message=resp.text, session_id=req.session_id)
        except Exception as e:
            logger.error(f"/api/chat error: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Failed to process message")

    @app.get("/api/history", tags=["Chat"], dependencies=[Depends(verify_key)])
    async def history(session_id: str = "default"):
        return {"history": agent.memory.get_conversation(session_id)}

    @app.post("/api/reset", tags=["Chat"], dependencies=[Depends(verify_key)])
    async def reset(req: ChatRequest):
        agent.clear_history(req.session_id)
        return {"status": "ok", "session_id": req.session_id}

    # Telegram webhook receiver (Vercel / serverless)
    @app.post("/api/telegram", tags=["Webhook"])
    async def telegram_webhook(payload: dict):
        # Actual processing delegated to TelegramAdapter when enabled
        return {"ok": True}

    return app
