import json
import tempfile
import unittest
from pathlib import Path

from hivesec_sentinel.config import Settings
from hivesec_sentinel.models import PublicAlert
from hivesec_sentinel.service import SentinelService, sanitize_public_text


class RecordingDelivery:
    def __init__(self, succeeds: bool = True) -> None:
        self.succeeds = succeeds
        self.alerts: list[PublicAlert] = []

    def send(self, alert: PublicAlert) -> bool:
        self.alerts.append(alert)
        return self.succeeds


class ServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.report = self.root / "latest.md"
        self.report.write_text(
            "\n".join(
                [
                    "# Butler Cyber Radar — 2026-06-29",
                    "",
                    "## Must (1)",
                    "",
                    "Critical issue",
                    "",
                    "## Worth (2)",
                    "## Monitor (3)",
                    "## Governance (4)",
                    "## Continuous Learning (1)",
                ]
            ),
            encoding="utf-8",
        )
        self.settings = Settings(
            data_dir=self.root / "data",
            butler_report=self.report,
        )

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_fallback_alert_is_bounded_and_critical(self) -> None:
        service = SentinelService(
            settings=self.settings,
            grok=None,
            telegram=None,
            github=None,
        )
        alert = service.build_alert()
        self.assertEqual(alert.severity, "critical")
        self.assertTrue(alert.degraded)
        self.assertEqual(alert.source, "HiveSec Sentinel")
        self.assertNotIn("Critical issue", alert.message)

    def test_publish_delivers_and_deduplicates(self) -> None:
        telegram = RecordingDelivery()
        github = RecordingDelivery()
        service = SentinelService(
            settings=self.settings,
            grok=None,
            telegram=telegram,  # type: ignore[arg-type]
            github=github,  # type: ignore[arg-type]
        )
        alert, status = service.publish()
        self.assertEqual(status, "published")
        self.assertEqual(len(telegram.alerts), 1)
        state = json.loads(self.settings.state_path.read_text(encoding="utf-8"))
        self.assertEqual(state["alert_id"], alert.id)

        _, repeated = service.publish()
        self.assertEqual(repeated, "unchanged")
        self.assertEqual(len(telegram.alerts), 1)

    def test_dry_run_has_no_state_or_delivery(self) -> None:
        telegram = RecordingDelivery()
        service = SentinelService(
            settings=self.settings,
            grok=None,
            telegram=telegram,  # type: ignore[arg-type]
            github=RecordingDelivery(),  # type: ignore[arg-type]
        )
        _, status = service.publish(dry_run=True)
        self.assertEqual(status, "dry-run")
        self.assertFalse(self.settings.state_path.exists())
        self.assertFalse(telegram.alerts)

    def test_redacts_credentials_from_public_text(self) -> None:
        marker = "abcdefghijklmnopqrstuvwxyz"
        text = " ".join(
            [
                f"xai-{marker}",
                f"123456789:{'A' * 35}",
                f"github_pat_{marker}",
            ]
        )
        result = sanitize_public_text(text)
        self.assertNotIn("abcdefghijklmnopqrstuvwxyz", result)
        self.assertEqual(result.count("[REDACTED]"), 3)


if __name__ == "__main__":
    unittest.main()
