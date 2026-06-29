"""Read a Butler report, enrich it and publish a bounded public alert."""

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

REPORT_DATE = re.compile(r"^# .+?(\d{4}-\d{2}-\d{2})", re.MULTILINE)
MUST_COUNT = re.compile(r"^## Must \((\d+)\)", re.MULTILINE)
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


def deterministic_summary(report: str, must_count: int) -> str:
    sections = {
        name: int(count)
        for name, count in re.findall(
            r"^## (Must|Worth|Monitor|Governance|Continuous Learning) \((\d+)\)",
            report,
            re.MULTILINE,
        )
    }
    if must_count:
        lead = f"• Foram identificados {must_count} item(ns) de prioridade MUST."
    else:
        lead = "• Não foram identificados itens de prioridade MUST nesta edição."
    return "\n".join(
        [
            lead,
            f"• Worth: {sections.get('Worth', 0)}; Monitor: {sections.get('Monitor', 0)}.",
            f"• Governance: {sections.get('Governance', 0)}; formação contínua: "
            f"{sections.get('Continuous Learning', 0)}.",
            "• Consultar o Cyber Radar e as fontes primárias antes de qualquer decisão.",
        ]
    )


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

    def build_alert(self, report_path: Path | None = None) -> PublicAlert:
        path = report_path or self.settings.butler_report
        if not path.is_file():
            raise FileNotFoundError(path)
        if path.stat().st_size > self.settings.max_report_bytes:
            raise ValueError("Butler report exceeds the configured size limit")
        report = path.read_text(encoding="utf-8")
        digest = hashlib.sha256(report.encode()).hexdigest()
        date_match = REPORT_DATE.search(report)
        report_date = date_match.group(1) if date_match else path.stem
        must_match = MUST_COUNT.search(report)
        must_count = int(must_match.group(1)) if must_match else 0
        degraded = False
        if self.grok is None:
            summary = deterministic_summary(report, must_count)
            degraded = True
        else:
            try:
                summary = self.grok.summarize(
                    report,
                    report_date=report_date,
                    must_count=must_count,
                )
            except ClientError:
                summary = deterministic_summary(report, must_count)
                degraded = True
        published_at = datetime.now(UTC).replace(microsecond=0).isoformat()
        return PublicAlert(
            schema_version=1,
            id=f"hivesec-{digest[:24]}",
            title=f"HiveSec Sentinel — {report_date}",
            message=sanitize_public_text(summary),
            severity="critical" if must_count else "info",
            source="HiveSec Sentinel",
            published_at=published_at,
            report_digest=digest,
            degraded=degraded,
        )

    def publish(
        self,
        *,
        report_path: Path | None = None,
        dry_run: bool = False,
        force: bool = False,
    ) -> tuple[PublicAlert, str]:
        alert = self.build_alert(report_path)
        if not force and self._published_digest() == alert.report_digest:
            return alert, "unchanged"
        if dry_run:
            return alert, "dry-run"
        if self.telegram is None or self.github is None:
            raise RuntimeError("Telegram and GitHub delivery must both be configured")
        outcomes = {
            "telegram": self.telegram.send(alert),
            "github": self.github.send(alert),
        }
        if not all(outcomes.values()):
            failed = ", ".join(name for name, ok in outcomes.items() if not ok)
            raise RuntimeError(f"Alert delivery failed: {failed}")
        self._save_state(alert)
        return alert, "published"

    def _published_digest(self) -> str:
        if not self.settings.state_path.is_file():
            return ""
        try:
            state = json.loads(self.settings.state_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return ""
        return str(state.get("report_digest", ""))

    def _save_state(self, alert: PublicAlert) -> None:
        self.settings.data_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        temporary = self.settings.state_path.with_suffix(".json.tmp")
        temporary.write_text(
            json.dumps(
                {
                    "report_digest": alert.report_digest,
                    "alert_id": alert.id,
                    "published_at": alert.published_at,
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        os.replace(temporary, self.settings.state_path)
