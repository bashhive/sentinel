"""CLI for explicit publication of validated public cybersecurity alerts."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from .feeds import record_published, refresh_kev
from .profile import resolve_public_brand
from .publisher import Publisher, alert_from_input
from .receipts import write_publication_receipts


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="hivesec-sentinel")
    command = parser.add_subparsers(dest="command", required=True)
    publish = command.add_parser("publish", help="Publish a validated public alert JSON file")
    publish.add_argument("input", type=Path)
    publish.add_argument("--dry-run", action="store_true")
    refresh = command.add_parser("refresh-kev", help="Check CISA KEV and emit new public alerts")
    refresh.add_argument("--state", type=Path, default=Path("data/feed_state.json"))
    refresh.add_argument("--lookback-days", type=int, default=7)
    refresh.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    try:
        public_context = resolve_public_brand(os.environ)
    except ValueError as error:
        parser.error(str(error))
    if args.command == "refresh-kev":
        if args.lookback_days < 1 or args.lookback_days > 30:
            parser.error("--lookback-days must be between 1 and 30")
        alerts, health = refresh_kev(
            state_path=args.state,
            user_agent=public_context.user_agent,
            lookback_days=args.lookback_days,
        )
        output = {"source_health": health.payload(), "alerts": alerts}
        if args.dry_run:
            print(json.dumps(output, ensure_ascii=False, indent=2))
            return 0 if health.status == "ok" else 1
        if health.status != "ok":
            return 1
        publisher = Publisher(
            telegram_token=os.environ.get("HIVESEC_TELEGRAM_BOT_TOKEN", ""),
            telegram_chat_id=os.environ.get("HIVESEC_TELEGRAM_CHAT_ID", ""),
            github_token=os.environ.get("HIVESEC_GITHUB_TOKEN", ""),
            repository=os.environ.get("HIVESEC_GITHUB_REPOSITORY", "bashhive/bash-website"),
            user_agent=public_context.user_agent,
        )
        published: list[dict[str, object]] = []
        for value in alerts:
            alert = alert_from_input(value)
            if publisher.publish(alert):
                write_publication_receipts(alert, public_context)
                published.append(value)
            else:
                print(f"publication failed for {alert.id}", file=__import__("sys").stderr)
                return 1
        record_published(args.state, published)
        return 0
    alert = alert_from_input(json.loads(args.input.read_text(encoding="utf-8")))
    if args.dry_run:
        print(json.dumps(alert.payload(), ensure_ascii=False))
        return 0
    publisher = Publisher(
        telegram_token=os.environ.get("HIVESEC_TELEGRAM_BOT_TOKEN", ""),
        telegram_chat_id=os.environ.get("HIVESEC_TELEGRAM_CHAT_ID", ""),
        github_token=os.environ.get("HIVESEC_GITHUB_TOKEN", ""),
        repository=os.environ.get("HIVESEC_GITHUB_REPOSITORY", "bashhive/bash-website"),
        user_agent=public_context.user_agent,
    )
    if not publisher.publish(alert):
        return 1
    write_publication_receipts(alert, public_context)
    return 0
