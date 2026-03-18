"""
Aspasia - Main Entry Point
Autonomous AI Bot for Telegram and Web
"""

import asyncio
import logging
from config import settings
from web.app import app
import uvicorn

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    """Main entry point"""
    logger.info(f"Starting {settings.agent_name}...")
    logger.info(f"API Server: {settings.host}:{settings.port}")
    logger.info(f"Model: {settings.agent_model}")
    logger.info(f"Telegram Bot: Enabled")
    
    # Run FastAPI server
    config = uvicorn.Config(
        app,
        host=settings.host,
        port=settings.port,
        log_level="info"
    )
    server = uvicorn.Server(config)
    await server.serve()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info(f"{settings.agent_name} shutting down...")
