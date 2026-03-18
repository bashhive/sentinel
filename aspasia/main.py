"""
Main entry point for Aspasia.

Orchestrates all components (Agent, Telegram, Web server).
"""

import asyncio
import logging
import signal
import sys
from typing import Optional

from aspasia.config import get_config
from aspasia.logging_config import setup_logging, get_logger
from aspasia.agent.core import Agent
from aspasia.integrations.claude_api import ClaudeAPI
from aspasia.integrations.telegram_handler import TelegramHandler
from aspasia.web.server import create_app
import uvicorn

# Global agent instance for dependency injection
_agent: Optional[Agent] = None

logger = get_logger(__name__)


def get_global_agent() -> Agent:
    """Get the global agent instance."""
    if _agent is None:
        raise RuntimeError("Agent not initialized")
    return _agent


async def initialize_agent(config: Config) -> Agent:
    """Initialize the agent."""
    logger.info("Initializing agent...")

    # Initialize Claude API client
    claude = ClaudeAPI(api_key=config.claude_api_key)

    # Create agent
    agent = Agent(config=config, claude_client=claude)

    logger.info(f"Agent '{config.agent_name}' initialized")
    return agent


async def run_telegram_bot(agent: Agent, config: Config) -> None:
    """Run Telegram bot handler."""
    if not config.telegram_bot_token:
        logger.info("Telegram bot not configured, skipping")
        return

    logger.info("Starting Telegram bot...")
    telegram = TelegramHandler(config=config, agent=agent)
    await telegram.initialize()

    # Run with polling
    try:
        await telegram.run_polling()
    except KeyboardInterrupt:
        logger.info("Telegram bot stopped")
        await telegram.stop()


async def run_web_server(config: Config) -> None:
    """Run the web server."""
    logger.info(f"Starting web server on {config.web_host}:{config.web_port}")

    app = create_app(config)

    config_obj = uvicorn.Config(
        app=app,
        host=config.web_host,
        port=config.web_port,
        reload=config.web_debug,
        log_level=config.log_level.lower(),
    )

    server = uvicorn.Server(config_obj)
    await server.serve()


async def main():
    """Main entry point."""
    global _agent

    # Load configuration
    try:
        config = get_config()
    except Exception as e:
        print(f"Configuration error: {str(e)}", file=sys.stderr)
        sys.exit(1)

    # Setup logging
    setup_logging(config)
    logger.info("=" * 80)
    logger.info(f"Aspasia v0.1.0 starting...")
    logger.info(f"Environment: {config.environment}")
    logger.info(f"Model: {config.claude_model}")
    logger.info("=" * 80)

    try:
        # Initialize agent
        _agent = await initialize_agent(config)

        # Start components based on configuration
        tasks = []

        # Always start web server
        tasks.append(asyncio.create_task(run_web_server(config)))

        # Start Telegram if configured
        if config.telegram_bot_token:
            tasks.append(asyncio.create_task(run_telegram_bot(_agent, config)))

        logger.info("Aspasia running. Press Ctrl+C to stop.")

        # Run until interrupted
        await asyncio.gather(*tasks)

    except KeyboardInterrupt:
        logger.info("Shutting down...")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}", exc_info=True)
        sys.exit(1)


def run():
    """Synchronous entry point for command line."""
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nShutdown complete")
        sys.exit(0)


if __name__ == "__main__":
    run()
