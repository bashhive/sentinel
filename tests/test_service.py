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
        self.outbox = self.root / "outbox"
        self.pending = self.outbox / "public"
        self.pending.mkdir(parents=True)
        self.event = self.pending / "breach-0123456789abcdef01234567.json"
        self.event.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "classification": "public",
                    "event_id": "breach-0123456789abcdef01234567",
                    "title": "Acme exposure",
                    "severity": "CRITICAL",
                    "confidence": 95,
                    "domain": "acme.example",
                    "source": "hibp",
                    "affected_count": 1_000_000,
                    "remediation": ["Alterar credenciais afetadas."],
                }
            ),
            encoding="utf-8",
        )
        self.settings = Settings(
            data_dir=self.root / "data",
            scanner_outbox_root=self.outbox,
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
        alert = service.build_alert(self.event)
        self.assertEqual(alert.severity, "critical")
        self.assertTrue(alert.degraded)
        self.assertEqual(alert.source, "HiveSec Sentinel")
        self.assertIn("1 000 000", alert.message)

    def test_consume_delivers_and_moves_event(self) -> None:
        telegram = RecordingDelivery()
        github = RecordingDelivery()
        service = SentinelService(
            settings=self.settings,
            grok=None,
            telegram=telegram,  # type: ignore[arg-type]
            github=github,  # type: ignore[arg-type]
        )
        counts = service.consume()
        self.assertEqual(counts["published"], 1)
        self.assertEqual(len(telegram.alerts), 1)
        self.assertFalse(self.event.exists())
        self.assertTrue((service.processed_dir / self.event.name).exists())

    def test_failed_delivery_leaves_event_pending(self) -> None:
        telegram = RecordingDelivery()
        github = RecordingDelivery(False)
        service = SentinelService(
            settings=self.settings,
            grok=None,
            telegram=telegram,  # type: ignore[arg-type]
            github=github,  # type: ignore[arg-type]
        )
        counts = service.consume()
        self.assertEqual(counts["failed"], 1)
        self.assertTrue(self.event.exists())
        self.assertEqual(len(telegram.alerts), 1)

        github.succeeds = True
        counts = service.consume()
        self.assertEqual(counts["published"], 1)
        self.assertEqual(len(telegram.alerts), 1)
        self.assertEqual(len(github.alerts), 2)

    def test_dry_run_has_no_delivery_or_move(self) -> None:
        telegram = RecordingDelivery()
        service = SentinelService(
            settings=self.settings,
            grok=None,
            telegram=telegram,  # type: ignore[arg-type]
            github=RecordingDelivery(),  # type: ignore[arg-type]
        )
        counts = service.consume(dry_run=True)
        self.assertEqual(counts["dry_run"], 1)
        self.assertTrue(self.event.exists())
        self.assertFalse(telegram.alerts)

    def test_private_identity_is_rejected(self) -> None:
        event = json.loads(self.event.read_text(encoding="utf-8"))
        event["victim"] = "owner@example.com"
        self.event.write_text(json.dumps(event), encoding="utf-8")
        service = SentinelService(
            settings=self.settings,
            grok=None,
            telegram=None,
            github=None,
        )
        with self.assertRaisesRegex(ValueError, "Private identity"):
            service.build_alert(self.event)

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
