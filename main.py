"""
aspasia_bot — entry point
Loads profile from PROFILE env var, wires core + adapters, starts server.

Usage:
    PROFILE=bash_pt python main.py
    PROFILE=aspasia_default python main.py
"""

import asyncio
import importlib
import logging
import uvicorn

from config.base import load_config
from core.agent import Agent
from core.claude_client import ClaudeClient
from core.tools import ToolRegistry

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


def load_profile(profile_name: str) -> dict:
    """Dynamically import profiles/<n>/profile.py and return PROFILE dict."""
    try:
        module = importlib.import_module(f"profiles.{profile_name}.profile")
        return module.PROFILE
    except ModuleNotFoundError:
        logger.warning(f"Profile '{profile_name}' not found — using aspasia_default")
        from profiles.aspasia_default.profile import PROFILE
        return PROFILE


async def main() -> None:
    # 1. Load infrastructure config
    cfg = load_config()
    logger.info(f"Environment : {cfg.environment}")
    logger.info(f"Profile     : {cfg.profile}")

    # 2. Load profile
    profile = load_profile(cfg.profile)
    agent_cfg = cfg.to_agent_config(profile)
    logger.info(f"Agent       : {agent_cfg['agent_name']} ({agent_cfg['model']})")

    # 3. Build core — tools first so profile can extend them
    tools = ToolRegistry()
    if callable(profile.get("register_tools")):
        profile["register_tools"](tools)
        logger.info(f"Tools       : {[t.name for t in tools.list_all()]}")

    client = ClaudeClient(api_key=cfg.anthropic_api_key)
    agent  = Agent(config=agent_cfg, client=client, tools=tools)

    # 4. Mount web adapter (always on — it's the API contract)
    if profile.get("web_enabled", True):
        from adapters.web.app import create_app
        web_app = create_app(
            agent=agent,
            cors_origins=profile.get("cors_origins"),
            api_key=profile.get("web_api_key"),
            title=profile.get("app_title", "Aspasia API"),
        )
    else:
        raise RuntimeError("web_enabled=False — at least the web adapter must run")

    # 5. Mount Telegram adapter (optional, profile-controlled)
    telegram_adapter = None
    if profile.get("telegram_enabled", False) and cfg.telegram_bot_token:
        from adapters.telegram.handler import TelegramAdapter
        telegram_adapter = TelegramAdapter(
            token=cfg.telegram_bot_token,
            agent=agent,
        )
        await telegram_adapter.initialize()
        logger.info("Telegram adapter: enabled")
    else:
        logger.info("Telegram adapter: disabled")

    # 6. Run
    logger.info(f"Web API     : http://{cfg.host}:{cfg.port}")

    server_cfg = uvicorn.Config(
        web_app,
        host=cfg.host,
        port=cfg.port,
        log_level="warning",
    )
    server = uvicorn.Server(server_cfg)

    if telegram_adapter:
        await asyncio.gather(
            server.serve(),
            telegram_adapter.run_polling(),
        )
    else:
        await server.serve()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Shutting down.")
