"""CLI for explicit publication of validated public cybersecurity alerts."""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path

from .adelaide import cache_path_for, remember_delivered, write_report
from .feeds import record_published, refresh_kev
from .profile import resolve_public_brand
from .publisher import Publisher, alert_from_input
from .receipts import write_publication_receipts

DEFAULT_MAX_BATCH = 25


def _configure_logging() -> None:
    """Send delivery outcomes to stderr so the LaunchAgent error log shows them."""
    if logging.getLogger().handlers:
        return
    logging.basicConfig(
        level=logging.INFO,
        stream=sys.stderr,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


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
    refresh.add_argument(
        "--bootstrap",
        action="store_true",
        help=(
            "First run only: ignore the lookback and publish the whole KEV catalogue. "
            "Without this flag a missing state file behaves like any other run."
        ),
    )
    refresh.add_argument(
        "--max-batch",
        type=int,
        default=DEFAULT_MAX_BATCH,
        help=(
            f"Maximum alerts published in one run (default {DEFAULT_MAX_BATCH}); "
            "the remainder is left for the next run. 0 means no limit."
        ),
    )
    refresh.add_argument(
        "--record-on",
        choices=("telegram", "all"),
        default="telegram",
        help=(
            "Which outcome marks an alert as seen. 'telegram' (default) records an alert "
            "whose Telegram delivery succeeded, so a blocked site channel cannot cause the "
            "same alert to be re-sent to the public bot every run. 'all' is the historical "
            "behaviour: record only when every configured channel accepted it."
        ),
    )
    report = command.add_parser(
        "adelaide-report",
        help=(
            "Write .adelaide/report.json from local state, receipts and cache only "
            "(no network, nothing is sent)"
        ),
    )
    report.add_argument("--state", type=Path, default=Path("data/feed_state.json"))
    args = parser.parse_args(argv)
    _configure_logging()
    if args.command == "adelaide-report":
        # Read-only over local state and never publishes, so it does not need
        # the public_brand publishing profile.
        return 0 if write_report(state_path=args.state) else 1
    try:
        public_context = resolve_public_brand(os.environ)
    except ValueError as error:
        parser.error(str(error))
    if args.command == "refresh-kev":
        if args.lookback_days < 1 or args.lookback_days > 30:
            parser.error("--lookback-days must be between 1 and 30")
        if args.max_batch < 0:
            parser.error("--max-batch must be 0 or greater")
        due_dates: dict[str, str] = {}
        alerts, health = refresh_kev(
            state_path=args.state,
            user_agent=public_context.user_agent,
            lookback_days=args.lookback_days,
            bootstrap=args.bootstrap,
            due_dates=due_dates,
        )
        withheld = 0
        if args.max_batch and len(alerts) > args.max_batch:
            withheld = len(alerts) - args.max_batch
            alerts = alerts[: args.max_batch]
        output = {
            "source_health": health.payload(),
            "withheld_for_next_run": withheld,
            "alerts": alerts,
        }
        if args.dry_run:
            print(json.dumps(output, ensure_ascii=False, indent=2))
            return 0 if health.status == "ok" else 1
        if health.status != "ok":
            write_report(state_path=args.state)
            return 1
        if withheld:
            print(
                f"publishing {len(alerts)} alert(s); {withheld} withheld for the next run",
                file=sys.stderr,
            )
        publisher = Publisher.from_env(os.environ, user_agent=public_context.user_agent)
        failed = False
        for value in alerts:
            alert = alert_from_input(value)
            outcome = publisher.publish_detailed(alert)
            delivered = tuple(channel for channel, ok in outcome.items() if ok)
            if delivered:
                write_publication_receipts(alert, public_context, channels=delivered)
            recorded = all(outcome.values()) if args.record_on == "all" else outcome["telegram"]
            if recorded:
                # Per alert, not per batch: an alert already accepted by the
                # channel we record on is never re-sent because a later alert
                # or another channel failed.
                record_published(args.state, [value])
                remember_delivered(cache_path_for(args.state), value, due_dates.get(alert.id))
            if not all(outcome.values()):
                rejected = ", ".join(channel for channel, ok in outcome.items() if not ok)
                print(
                    f"publication failed for {alert.id}: channel(s) {rejected} "
                    f"(recorded as seen: {recorded})",
                    file=sys.stderr,
                )
                failed = True
                break
        write_report(state_path=args.state)
        return 1 if failed else 0
    alert = alert_from_input(json.loads(args.input.read_text(encoding="utf-8")))
    if args.dry_run:
        print(json.dumps(alert.payload(), ensure_ascii=False))
        return 0
    publisher = Publisher.from_env(os.environ, user_agent=public_context.user_agent)
    outcome = publisher.publish_detailed(alert)
    delivered = tuple(channel for channel, ok in outcome.items() if ok)
    if delivered:
        write_publication_receipts(alert, public_context, channels=delivered)
    if not all(outcome.values()):
        rejected = ", ".join(channel for channel, ok in outcome.items() if not ok)
        print(f"publication failed for {alert.id}: channel(s) {rejected}", file=sys.stderr)
        return 1
    return 0
