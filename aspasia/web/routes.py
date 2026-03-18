"""API routes for Aspasia web server."""

import logging
from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime

from aspasia.agent.core import Agent
from aspasia.web.models import (
    ChatRequest,
    ChatResponse,
    HistoryResponse,
    UserContextResponse,
    HealthResponse,
    StatsResponse,
    PreferenceRequest,
    ErrorResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["agent"])


def get_agent() -> Agent:
    """Dependency to get agent instance."""
    # This will be injected by the server
    from aspasia.main import get_global_agent

    return get_global_agent()


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, agent: Agent = Depends(get_agent)):
    """Send a message to the agent and get a response."""
    try:
        response = await agent.process_message(
            user_id=request.user_id,
            message=request.message,
            context=request.context,
        )
        return ChatResponse(
            text=response.text,
            user_id=response.user_id,
            timestamp=response.timestamp.isoformat(),
            metadata=response.metadata,
        )
    except Exception as e:
        logger.error(f"Chat error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/chat/{user_id}/history", response_model=HistoryResponse)
async def get_history(
    user_id: str, limit: int = 10, agent: Agent = Depends(get_agent)
):
    """Get conversation history for a user."""
    try:
        messages = agent.memory.get_conversation(user_id, limit=limit)
        return HistoryResponse(user_id=user_id, messages=messages, count=len(messages))
    except Exception as e:
        logger.error(f"History fetch error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/chat/{user_id}/context", response_model=UserContextResponse)
async def get_user_context(user_id: str, agent: Agent = Depends(get_agent)):
    """Get context and preferences for a user."""
    try:
        context = agent.memory.get_user_context(user_id)
        return UserContextResponse(
            user_id=context["user_id"],
            created_at=context["created_at"],
            last_interaction=context["last_interaction"],
            message_count=context["message_count"],
            preferences=context["preferences"],
            facts=context["facts"],
        )
    except Exception as e:
        logger.error(f"Context fetch error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat/{user_id}/preference")
async def set_preference(
    user_id: str, request: PreferenceRequest, agent: Agent = Depends(get_agent)
):
    """Set a user preference."""
    try:
        agent.memory.set_user_preference(user_id, request.key, request.value)
        return {
            "status": "ok",
            "user_id": user_id,
            "key": request.key,
            "value": request.value,
        }
    except Exception as e:
        logger.error(f"Preference set error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/chat/{user_id}/history")
async def clear_history(user_id: str, agent: Agent = Depends(get_agent)):
    """Clear conversation history for a user."""
    try:
        agent.clear_user_history(user_id)
        return {"status": "ok", "user_id": user_id, "message": "History cleared"}
    except Exception as e:
        logger.error(f"History clear error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agent/health", response_model=HealthResponse)
async def health_check(agent: Agent = Depends(get_agent)):
    """Check agent health."""
    try:
        checks = await agent.health_check()
        return HealthResponse(
            agent=checks["agent"],
            memory=checks["memory"],
            claude=checks["claude"],
            timestamp=checks["timestamp"],
        )
    except Exception as e:
        logger.error(f"Health check error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agent/stats", response_model=StatsResponse)
async def get_stats(agent: Agent = Depends(get_agent)):
    """Get agent statistics."""
    try:
        stats = agent.get_stats()
        return StatsResponse(
            agent_name=stats["agent_name"],
            model=stats["model"],
            timestamp=stats["timestamp"],
            memory=stats["memory"],
            tools_available=stats["tools_available"],
        )
    except Exception as e:
        logger.error(f"Stats fetch error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def server_health():
    """Simple health check endpoint."""
    return {"status": "ok", "timestamp": datetime.now().isoformat()}
