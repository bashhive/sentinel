"""FastAPI web server for Aspasia."""

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from aspasia.config import Config
from aspasia.web import routes

logger = logging.getLogger(__name__)


def create_app(config: Config) -> FastAPI:
    """Create and configure FastAPI application."""

    app = FastAPI(
        title="Aspasia",
        description="Autonomous AI Agent Bot",
        version="0.1.0",
    )

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routes
    app.include_router(routes.router)

    # Static files
    static_path = Path(__file__).parent / "static"
    if static_path.exists():
        app.mount(
            "/static",
            StaticFiles(directory=str(static_path)),
            name="static",
        )

    @app.get("/")
    async def root():
        """Root endpoint."""
        return {
            "name": "Aspasia",
            "version": "0.1.0",
            "status": "running",
            "endpoints": [
                "POST /api/chat",
                "GET /api/chat/{user_id}/history",
                "GET /api/chat/{user_id}/context",
                "POST /api/chat/{user_id}/preference",
                "DELETE /api/chat/{user_id}/history",
                "GET /api/agent/health",
                "GET /api/agent/stats",
                "GET /health",
            ],
        }

    logger.info("FastAPI application created")
    return app


async def run_server(config: Config):
    """Run the web server."""
    import uvicorn

    logger.info(f"Starting web server on {config.web_host}:{config.web_port}")

    config = uvicorn.Config(
        app="aspasia.web.server:create_app",
        host=config.web_host,
        port=config.web_port,
        reload=config.web_debug,
        log_level=config.log_level.lower(),
    )

    server = uvicorn.Server(config)
    await server.serve()
