"""HiveSec Sentinel command-line interface."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence

from hivesec_sentinel import __version__
from hivesec_sentinel.clients import GitHubDispatchClient, GrokClient, TelegramClient
from hivesec_sentinel.config import Settings
from hivesec_sentinel.service import SentinelService


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="hivesec-sentinel")
    root.add_argument("--version", action="version", version=__version__)
    commands = root.add_subparsers(dest="command", required=True)
    commands.add_parser("health")
    consume = commands.add_parser("consume")
    consume.add_argument("--dry-run", action="store_true")
    consume.add_argument("--limit", type=int, default=20)
    return root


def build_service(settings: Settings) -> SentinelService:
    grok = (
        GrokClient(
            base_url=settings.grok_base_url,
            model=settings.grok_model,
            api_key=settings.xai_api_key,
            timeout_seconds=settings.timeout_seconds,
        )
        if settings.xai_api_key
        else None
    )
    telegram = (
        TelegramClient(
            token=settings.telegram_bot_token,
            chat_id=settings.telegram_chat_id,
            timeout_seconds=settings.timeout_seconds,
        )
        if settings.telegram_bot_token and settings.telegram_chat_id
        else None
    )
    github = (
        GitHubDispatchClient(
            repository=settings.github_repository,
            token=settings.github_token,
            timeout_seconds=settings.timeout_seconds,
        )
        if settings.github_repository and settings.github_token
        else None
    )
    return SentinelService(settings=settings, grok=grok, telegram=telegram, github=github)


def main(argv: Sequence[str] | None = None) -> int:
    args = parser().parse_args(argv)
    settings = Settings.from_env()
    try:
        service = build_service(settings)
        if args.command == "health":
            pending = (
                len(list(service.pending_dir.glob("breach-*.json")))
                if service.pending_dir.exists()
                else 0
            )
            print(
                json.dumps(
                    {
                        "service": "hivesec-sentinel",
                        "version": __version__,
                        "configured": settings.configured,
                        "scanner_public_outbox": str(service.pending_dir),
                        "pending": pending,
                        "telegram_bot": f"@{settings.telegram_bot_username}",
                        "github_repository": settings.github_repository,
                    }
                )
            )
            return 0
        counts = service.consume(dry_run=args.dry_run, limit=args.limit)
        print(json.dumps({"status": "ok", **counts}))
        return 1 if counts["failed"] else 0
    except (ValueError, RuntimeError, OSError) as error:
        print(json.dumps({"status": "error", "error": str(error)}), file=sys.stderr)
        return 1
