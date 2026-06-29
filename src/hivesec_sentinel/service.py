"""Consume public scanner events and publish bounded public alerts."""

from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import UTC, datetime
from pathlib import Path

from hivesec_sentinel.clients import ClientError, GitHubDispatchClient, GrokClient, TelegramClient
from hivesec_sentinel.config import Settings
from hivesec_sentinel.models import PublicAlert

EVENT_ID = re.compile(r"^breach-([a-f0-9]{24})$")
SECRET_PATTERNS = (
    re.compile(r"\b(?:xai-|sk-|gsk_)[A-Za-z0-9_-]{16,}\b"),
    re.compile(r"\b[0-9]{8,12}:[A-Za-z0-9_-]{30,}\b"),
    re.compile(r"\b(?:github_pat_|ghp_)[A-Za-z0-9_]{20,}\b"),
)


def sanitize_public_text(text: str, *, maximum: int = 3500) -> str:
    cleaned = "".join(character for character in text if character >= " " or character in "\n\t")
    for pattern in SECRET_PATTERNS:
        cleaned = pattern.sub("[REDACTED]", cleaned)
    return cleaned.strip()[:maximum]


def deterministic_summary(event: dict[str, object]) -> str:
    try:
        affected = int(str(event.get("affected_count", 0) or 0))
    except ValueError:
        affected = 0
    domain = sanitize_public_text(str(event.get("domain", "")), maximum=200)
    source = sanitize_public_text(str(event.get("source", "fonte pública")), maximum=100)
    remediation = event.get("remediation", [])
    actions = (
        [sanitize_public_text(str(item), maximum=300) for item in remediation[:3]]
        if isinstance(remediation, list)
        else []
    )
    lines = [
        f"• Exposição reportada por {source}" + (f" associada a {domain}." if domain else "."),
        f"• Contas/registos potencialmente afetados: {affected:,}.".replace(",", " "),
    ]
    lines.extend(f"• {action}" for action in actions if action)
    return "\n".join(lines)


class SentinelService:
    def __init__(
        self,
        *,
        settings: Settings,
        grok: GrokClient | None,
        telegram: TelegramClient | None,
        github: GitHubDispatchClient | None,
    ) -> None:
        self.settings = settings
        self.grok = grok
        self.telegram = telegram
        self.github = github

    @property
    def pending_dir(self) -> Path:
        return self.settings.scanner_outbox_root / "public"

    @property
    def processed_dir(self) -> Path:
        return self.settings.scanner_outbox_root / "processed" / "public"

    def load_event(self, path: Path) -> dict[str, object]:
        if path.is_symlink() or not path.is_file():
            raise ValueError("Public event must be a regular file")
        if path.parent.resolve() != self.pending_dir.resolve():
            raise ValueError("Public event is outside the public outbox")
        if path.stat().st_size > self.settings.max_event_bytes:
            raise ValueError("Public event exceeds the configured size limit")
        event = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(event, dict):
            raise ValueError("Public event must be a JSON object")
        if event.get("schema_version") != 1 or event.get("classification") != "public":
            raise ValueError("Invalid public event contract")
        event_id = str(event.get("event_id", ""))
        if EVENT_ID.fullmatch(event_id) is None or path.name != f"{event_id}.json":
            raise ValueError("Invalid public event identifier")
        if "victim" in event:
            raise ValueError("Private identity found in public event")
        return event

    def build_alert(self, path: Path) -> PublicAlert:
        event = self.load_event(path)
        digest = hashlib.sha256(
            json.dumps(event, ensure_ascii=False, sort_keys=True).encode()
        ).hexdigest()
        degraded = False
        if self.grok is None:
            summary = deterministic_summary(event)
            degraded = True
        else:
            try:
                summary = self.grok.summarize_event(event)
            except ClientError:
                summary = deterministic_summary(event)
                degraded = True
        event_id = str(event["event_id"])
        event_id_match = EVENT_ID.fullmatch(event_id)
        if event_id_match is None:
            raise ValueError("Invalid public event identifier")
        severity = str(event.get("severity", "HIGH")).upper()
        title = sanitize_public_text(str(event.get("title", "Alerta")), maximum=180)
        return PublicAlert(
            schema_version=1,
            id=f"hivesec-{event_id_match.group(1)}",
            title=f"HiveSec Sentinel — {title}",
            message=sanitize_public_text(summary),
            severity="critical" if severity == "CRITICAL" else "warning",
            source="HiveSec Sentinel",
            published_at=datetime.now(UTC).replace(microsecond=0).isoformat(),
            event_digest=digest,
            degraded=degraded,
        )

    def consume(self, *, dry_run: bool = False, limit: int = 20) -> dict[str, int]:
        counts = {"pending": 0, "published": 0, "failed": 0, "dry_run": 0}
        if not self.pending_dir.exists():
            return counts
        paths = sorted(self.pending_dir.glob("breach-*.json"))[: max(0, limit)]
        counts["pending"] = len(paths)
        for path in paths:
            try:
                alert = self.build_alert(path)
                if dry_run:
                    counts["dry_run"] += 1
                    continue
                if self.telegram is None or self.github is None:
                    raise RuntimeError("Telegram and GitHub delivery must both be configured")
                if not self.telegram.send(alert) or not self.github.send(alert):
                    raise RuntimeError("Public alert delivery failed")
                self._mark_processed(path)
                counts["published"] += 1
            except (ClientError, ValueError, RuntimeError, OSError, json.JSONDecodeError):
                counts["failed"] += 1
        return counts

    def _mark_processed(self, path: Path) -> None:
        self.processed_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        destination = self.processed_dir / path.name
        os.replace(path, destination)
