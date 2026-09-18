from __future__ import annotations

import json
import stat
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pytest

from hivesec_sentinel import adelaide, cli
from hivesec_sentinel.adelaide import (
    BOT,
    CACHE_MAX_ENTRIES,
    build_report,
    cache_path_for,
    load_cache,
    remember_delivered,
    write_report,
)
from hivesec_sentinel.feeds import SourceHealth, kev_alerts
from hivesec_sentinel.publisher import alert_from_input

NOW = datetime(2026, 9, 18, 12, 0, tzinfo=UTC)


def alert(cve: str, name: str = "Example remote code execution") -> dict[str, object]:
    return {
        "schema_version": 1,
        "id": f"hivesec-kev-{cve.lower()}",
        "title": f"CISA KEV: {name}",
        "message": (
            f"CISA has added {cve} to its Known Exploited Vulnerabilities catalog. "
            "Affected: Example Vendor Example Product. Recommended action: Patch."
        ),
        "severity": "critical",
        "source": "HiveSec Sentinel",
        "published_at": "2026-09-17T00:00:00+00:00",
    }


def write_state(path: Path, *, status: str = "ok", checked: datetime = NOW) -> Path:
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "seen_ids": ["hivesec-kev-cve-2026-0001"],
                "source_health": [
                    {
                        "name": "CISA KEV",
                        "checked_at": checked.isoformat(),
                        "status": status,
                        "detail": "HTTP 503",
                    }
                ],
                "last_checked_at": checked.isoformat(),
                "last_published_at": (NOW - timedelta(hours=1)).isoformat(),
            }
        ),
        encoding="utf-8",
    )
    return path


def receipt(directory: Path, alert_id: str, delivered: datetime, channel: str = "telegram") -> None:
    directory.mkdir(exist_ok=True)
    (directory / f"{alert_id}-{channel}.json").write_text(
        json.dumps(
            {"public_event_id": alert_id, "channel": channel, "delivered_at": delivered.isoformat()}
        ),
        encoding="utf-8",
    )


def test_kev_due_dates_travel_beside_the_public_alert() -> None:
    catalog = {
        "vulnerabilities": [
            {
                "cveID": "CVE-2026-1000",
                "dateAdded": "2026-09-17",
                "dueDate": "2026-10-08",
                "vulnerabilityName": "Example",
                "vendorProject": "V",
                "product": "P",
            }
        ]
    }
    due: dict[str, str] = {}
    alerts = kev_alerts(catalog, since=date(2026, 9, 1), seen_ids=set(), due_dates=due)
    assert due == {"hivesec-kev-cve-2026-1000": "2026-10-08"}
    assert "dueDate" not in alerts[0] and "due_date" not in alerts[0]
    alert_from_input(alerts[0])  # the strict PublicAlert contract still accepts it


def test_cache_is_private_bounded_and_expires(tmp_path: Path) -> None:
    cache = cache_path_for(tmp_path / "feed_state.json")
    remember_delivered(cache, alert("CVE-2026-0001"), "2026-09-20", now=NOW - timedelta(days=8))
    for index in range(CACHE_MAX_ENTRIES + 5):
        remember_delivered(
            cache, alert(f"CVE-2026-{index + 100}"), None, now=NOW + timedelta(minutes=index)
        )
    entries = load_cache(cache)
    assert len(entries) == CACHE_MAX_ENTRIES
    assert "hivesec-kev-cve-2026-0001" not in {entry["id"] for entry in entries}
    assert stat.S_IMODE(cache.stat().st_mode) == 0o600
    assert entries[-1]["summary"].endswith("Known Exploited Vulnerabilities catalog.")
    assert "Recommended action" not in entries[-1]["summary"]


def test_report_contract_priorities_and_ordering(tmp_path: Path) -> None:
    state = write_state(tmp_path / "feed_state.json")
    cache = cache_path_for(state)
    receipts = tmp_path / "receipts"
    remember_delivered(cache, alert("CVE-2026-0002", "Due soon"), "2026-09-22", now=NOW)
    remember_delivered(cache, alert("CVE-2026-0003", "Due later"), "2026-10-09", now=NOW)
    remember_delivered(
        cache, alert("CVE-2026-0004", "Old"), "2026-09-19", now=NOW - timedelta(hours=49)
    )
    receipt(receipts, "hivesec-kev-cve-2026-0005", NOW - timedelta(hours=2))
    receipt(receipts, "hivesec-kev-cve-2026-0006", NOW - timedelta(hours=2), channel="site")

    report = build_report(state_path=state, receipt_dir=receipts, now=NOW)

    assert report["version"] == 1 and report["repo"] == "sentinel" and report["bot"] == BOT
    assert report["generated_at"] == "2026-09-18T12:00:00Z"
    titles = [item["title"] for item in report["items"]]
    assert titles == [
        "CISA KEV: Due soon",
        "CISA KEV: Due later",
        "CISA KEV: CVE-2026-0005",
        "KEV feed health: ok",
    ]
    first, second, fallback, status = report["items"]
    assert first["priority"] == "urgent" and first["due_date"] == "2026-09-22"
    assert first["url"] == "https://nvd.nist.gov/vuln/detail/CVE-2026-0002"
    assert second["priority"] == "high"
    assert fallback["priority"] == "high" and fallback["due_date"] is None
    assert status["kind"] == "status" and status["priority"] == "low"
    assert "3 alert(s) delivered to @hivesecsentinelbot" in status["summary"]
    for item in report["items"]:
        assert set(item) == {"title", "priority", "summary", "url", "due_date", "kind"}
        assert len(item["title"]) <= 200 and len(item["summary"]) <= 400
        assert item["url"].startswith("https://")


@pytest.mark.parametrize(
    ("status", "checked", "title"),
    [
        ("error", NOW, "KEV feed health: error"),
        ("ok", NOW - timedelta(hours=13), "KEV feed health: stale"),
    ],
)
def test_degraded_health_is_high_and_first_among_high(
    tmp_path: Path, status: str, checked: datetime, title: str
) -> None:
    state = write_state(tmp_path / "feed_state.json", status=status, checked=checked)
    remember_delivered(cache_path_for(state), alert("CVE-2026-0007"), None, now=NOW)
    report = build_report(state_path=state, receipt_dir=tmp_path / "none", now=NOW)
    assert report["items"][0]["title"] == title
    assert report["items"][0]["priority"] == "high"
    assert report["items"][1]["kind"] == "alert"


def test_missing_state_still_reports_status(tmp_path: Path) -> None:
    report = build_report(
        state_path=tmp_path / "missing.json", receipt_dir=tmp_path / "none", now=NOW
    )
    assert [item["kind"] for item in report["items"]] == ["status"]
    assert report["items"][0]["priority"] == "high"


def test_report_is_capped_to_twenty_items(tmp_path: Path) -> None:
    state = write_state(tmp_path / "feed_state.json")
    for index in range(30):
        remember_delivered(
            cache_path_for(state),
            alert(f"CVE-2026-{index + 200}"),
            None,
            now=NOW - timedelta(minutes=index),
        )
    report = build_report(state_path=state, receipt_dir=tmp_path / "none", now=NOW)
    assert len(report["items"]) == 20
    assert sum(item["kind"] == "status" for item in report["items"]) == 1


def test_write_report_is_atomic_and_private(tmp_path: Path) -> None:
    state = write_state(tmp_path / "feed_state.json")
    target = tmp_path / "repo" / ".adelaide" / "report.json"
    assert write_report(state_path=state, report_path=target, receipt_dir=tmp_path, now=NOW)
    assert stat.S_IMODE(target.stat().st_mode) == 0o600
    assert stat.S_IMODE(target.parent.stat().st_mode) == 0o700
    assert [path.name for path in target.parent.iterdir()] == ["report.json"]
    assert target.stat().st_size <= 65536
    assert json.loads(target.read_text(encoding="utf-8"))["version"] == 1


def test_write_report_never_raises(tmp_path: Path, monkeypatch, caplog) -> None:
    def boom(**_: object) -> dict[str, object]:
        raise RuntimeError("boom")

    monkeypatch.setattr(adelaide, "build_report", boom)
    assert write_report(state_path=tmp_path / "s.json", report_path=tmp_path / "r.json") is False
    assert len(caplog.records) == 1
    blocker = tmp_path / "not-a-dir"
    blocker.write_text("", encoding="utf-8")
    remember_delivered(blocker / "cache.json", alert("CVE-2026-0008"))  # contained, no raise
    assert len(caplog.records) == 2
    assert "adelaide cache not updated" in caplog.records[-1].getMessage()


def test_cli_adelaide_report_needs_no_profile_or_network(tmp_path: Path, monkeypatch) -> None:
    for name in ("SENTINEL_EXECUTION_PROFILE", "SENTINEL_ATTRIBUTION_APPROVAL_REF"):
        monkeypatch.delenv(name, raising=False)
    target = tmp_path / "report.json"
    calls: list[Path] = []

    def fake_write_report(*, state_path: Path) -> bool:
        calls.append(state_path)
        return write_report(state_path=state_path, report_path=target, receipt_dir=tmp_path)

    monkeypatch.setattr(cli, "write_report", fake_write_report)
    state = write_state(tmp_path / "feed_state.json", checked=datetime.now(UTC))
    assert cli.main(["adelaide-report", "--state", str(state)]) == 0
    assert calls == [state]
    assert json.loads(target.read_text(encoding="utf-8"))["items"][-1]["kind"] == "status"


class FakePublisher:
    def publish_detailed(self, _alert: object) -> dict[str, bool]:
        return {"telegram": True}


def test_refresh_kev_records_cache_and_writes_report(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("SENTINEL_EXECUTION_PROFILE", "public_brand")
    monkeypatch.setenv("SENTINEL_ATTRIBUTION_APPROVAL_REF", "TEST-REF-001")
    state = write_state(tmp_path / "feed_state.json", checked=datetime.now(UTC))
    new = alert("CVE-2026-0009", "Fresh")

    def fake_refresh(*, due_dates: dict[str, str], **_: object):
        due_dates[str(new["id"])] = "2026-09-20"
        return [new], SourceHealth("CISA KEV", NOW.isoformat(), "ok", "1 new")

    reports: list[Path] = []
    monkeypatch.setattr(cli, "refresh_kev", fake_refresh)
    monkeypatch.setattr(cli.Publisher, "from_env", classmethod(lambda *a, **k: FakePublisher()))
    monkeypatch.setattr(cli, "write_publication_receipts", lambda *a, **k: None)
    monkeypatch.setattr(cli, "write_report", lambda *, state_path: reports.append(state_path))

    assert cli.main(["refresh-kev", "--state", str(state)]) == 0
    cached = load_cache(cache_path_for(state))
    assert [(e["title"], e["due_date"]) for e in cached] == [("CISA KEV: Fresh", "2026-09-20")]
    assert reports == [state]


def test_refresh_kev_writes_report_on_health_failure(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("SENTINEL_EXECUTION_PROFILE", "public_brand")
    monkeypatch.setenv("SENTINEL_ATTRIBUTION_APPROVAL_REF", "TEST-REF-001")
    reports: list[Path] = []
    monkeypatch.setattr(
        cli,
        "refresh_kev",
        lambda **_: ([], SourceHealth("CISA KEV", NOW.isoformat(), "error", "HTTP 503")),
    )
    monkeypatch.setattr(cli, "write_report", lambda *, state_path: reports.append(state_path))
    assert cli.main(["refresh-kev", "--state", str(tmp_path / "s.json")]) == 1
    assert reports == [tmp_path / "s.json"]
