"""
HiveSec Sentinel bot — entry point.

Loads the profile from the PROFILE env var, wires core + adapters.

Two run modes share one builder (`build_app`):
  * Serverless (Vercel @vercel/python): imports the module-level `app` (ASGI).
  * Local/long-running: `python main.py` starts uvicorn and (optionally) Telegram.

Usage (local):
    PROFILE=bash_pt python main.py
    PROFILE=hivesec_default python main.py
"""

import importlib
import logging

from config.base import load_config
from core.agent import Agent
from core.llm_client import make_client
from core.tools import ToolRegistry

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


def load_profile(profile_name: str) -> dict:
    """Dynamically import profiles/<name>/profile.py and return PROFILE dict."""
    try:
        module = importlib.import_module(f"profiles.{profile_name}.profile")
        return module.PROFILE
    except ModuleNotFoundError:
        logger.warning(f"Profile '{profile_name}' not found — using hivesec_default")
        from profiles.hivesec_default.profile import PROFILE
        return PROFILE


def build_agent():
    """Build the configured Agent (config + profile + tools + LLM client)."""
    cfg = load_config()
    profile = load_profile(cfg.profile)
    agent_cfg = cfg.to_agent_config(profile)
    logger.info(f"Profile     : {cfg.profile}")
    logger.info(f"Agent       : {agent_cfg['agent_name']} ({agent_cfg['model']})")

    tools = ToolRegistry()
    if callable(profile.get("register_tools")):
        profile["register_tools"](tools)
        logger.info(f"Tools       : {[t.name for t in tools.list_all()]}")

    # Pluggable, free-tier-first LLM client (Groq by default — no API cost).
    client = make_client(
        provider=cfg.llm_provider,
        groq_api_key=cfg.resolved_llm_key,
        anthropic_api_key=cfg.anthropic_api_key,
        base_url=cfg.llm_base_url,
        probe_model=cfg.probe_model,
    )
    logger.info(f"LLM provider: {cfg.llm_provider}")
    return Agent(config=agent_cfg, client=client, tools=tools), profile


def build_app():
    """Build and return the FastAPI ASGI app. Used by both run modes."""
    agent, profile = build_agent()
    if not profile.get("web_enabled", True):
        raise RuntimeError("web_enabled=False — at least the web adapter must run")
    from adapters.web.app import create_app
    return create_app(
        agent=agent,
        cors_origins=profile.get("cors_origins"),
        api_key=profile.get("web_api_key"),
        title=profile.get("app_title", "HiveSec Sentinel API"),
    )


# Module-level ASGI app — this is what Vercel's @vercel/python serves.
app = build_app()


def _run_local() -> None:
    """Local/long-running mode: uvicorn + optional Telegram polling."""
    import asyncio
    import uvicorn

    cfg = load_config()
    profile = load_profile(cfg.profile)

    async def _serve() -> None:
        telegram_adapter = None
        if profile.get("telegram_enabled", False) and cfg.telegram_bot_token:
            # Rebuild an agent that the Telegram adapter can share.
            from adapters.telegram.handler import TelegramAdapter
            agent, _ = build_agent()
            telegram_adapter = TelegramAdapter(token=cfg.telegram_bot_token, agent=agent)
            await telegram_adapter.initialize()
            logger.info("Telegram adapter: enabled")
        else:
            logger.info("Telegram adapter: disabled")

        logger.info(f"Web API     : http://{cfg.host}:{cfg.port}")
        server = uvicorn.Server(uvicorn.Config(
            app, host=cfg.host, port=cfg.port, log_level="warning",
        ))
        if telegram_adapter:
            await asyncio.gather(server.serve(), telegram_adapter.run_polling())
        else:
            await server.serve()

    asyncio.run(_serve())


if __name__ == "__main__":
    try:
        _run_local()
    except KeyboardInterrupt:
        logger.info("Shutting down.")
