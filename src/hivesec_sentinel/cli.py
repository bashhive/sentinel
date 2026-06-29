"""HiveSec Sentinel command-line interface."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from hivesec_sentinel import __version__
from hivesec_sentinel.clients import GitHubDispatchClient, GrokClient, TelegramClient
from hivesec_sentinel.config import Settings
from hivesec_sentinel.service import SentinelService


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="hivesec-sentinel")
    root.add_argument("--version", action="version", version=__version__)
    commands = root.add_subparsers(dest="command", required=True)
    commands.add_parser("health")
    publish = commands.add_parser("publish")
    publish.add_argument("--report", type=Path)
    publish.add_argument("--dry-run", action="store_true")
    publish.add_argument("--force", action="store_true")
    commands.add_parser("delivery-test")
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
    return SentinelService(
        settings=settings,
        grok=grok,
        telegram=telegram,
        github=github,
    )


def main(argv: Sequence[str] | None = None) -> int:
    args = parser().parse_args(argv)
    settings = Settings.from_env()
    try:
        if args.command == "health":
            print(
                json.dumps(
                    {
                        "service": "hivesec-sentinel",
                        "version": __version__,
                        "configured": settings.configured,
                        "report": str(settings.butler_report),
                        "report_ready": settings.butler_report.is_file(),
                        "telegram_bot": f"@{settings.telegram_bot_username}",
                        "github_repository": settings.github_repository,
                    }
                )
            )
            return 0
        service = build_service(settings)
        if args.command == "delivery-test":
            if service.telegram is None or service.github is None:
                raise RuntimeError("Telegram and GitHub delivery are not configured")
            alert = service.build_alert()
            outcomes = {
                "telegram": service.telegram.send(alert),
                "github": service.github.send(alert),
            }
            if not all(outcomes.values()):
                raise RuntimeError(f"Delivery test failed: {outcomes}")
            print(json.dumps({"status": "sent", **outcomes}))
            return 0
        alert, status = service.publish(
            report_path=args.report,
            dry_run=args.dry_run,
            force=args.force,
        )
        print(
            json.dumps(
                {
                    "status": status,
                    "alert": alert.public_dict(),
                    "degraded": alert.degraded,
                },
                ensure_ascii=False,
            )
        )
        return 0
    except (FileNotFoundError, ValueError, RuntimeError, OSError) as error:
        print(json.dumps({"status": "error", "error": str(error)}), file=sys.stderr)
        return 1
