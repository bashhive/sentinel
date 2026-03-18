"""
Web Application - FastAPI server for Aspasia
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from config import settings
from agent.core import get_agent
import logging


logger = logging.getLogger(__name__)

app = FastAPI(
    title="Aspasia API",
    description="Web API for Aspasia AI Assistant",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Data models
class ChatRequest(BaseModel):
    """Chat message request"""
    message: str
    session_id: str = "default"


class ChatResponse(BaseModel):
    """Chat message response"""
    message: str
    session_id: str


class StatusResponse(BaseModel):
    """Status response"""
    status: str
    agent_name: str
    model: str
    uptime: str


# Initialize agent
agent = get_agent()


# Routes
@app.get("/", tags=["Health"])
async def root():
    """Root endpoint"""
    return {
        "name": "Aspasia API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/api/status", response_model=StatusResponse, tags=["Status"])
async def get_status():
    """Get bot status"""
    return {
        "status": "online",
        "agent_name": agent.name,
        "model": agent.model,
        "uptime": "running"
    }


@app.post("/api/chat", response_model=ChatResponse, tags=["Chat"])
async def chat(request: ChatRequest):
    """Send a message to Aspasia"""
    try:
        response = agent.chat(request.message)
        return ChatResponse(
            message=response,
            session_id=request.session_id
        )
    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}")
        raise HTTPException(status_code=500, detail="Failed to process message")


@app.get("/api/history", tags=["Chat"])
async def get_history():
    """Get conversation history"""
    return {
        "history": agent.get_history()
    }


@app.post("/api/reset", tags=["Chat"])
async def reset_conversation():
    """Reset conversation"""
    agent.reset_conversation()
    return {"status": "conversation reset"}


@app.post("/api/telegram", tags=["Webhook"])
async def telegram_webhook(request: dict):
    """Telegram webhook receiver"""
    try:
        # This would integrate with telegram bot
        # For now, just acknowledge
        return {"ok": True}
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        raise HTTPException(status_code=500, detail="Webhook processing failed")


@app.get("/api/health", tags=["Health"])
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "Aspasia",
        "timestamp": __import__('datetime').datetime.now().isoformat()
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )
