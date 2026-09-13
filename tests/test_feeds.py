from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Self

from hivesec_sentinel.feeds import KEV_URL, kev_alerts, load_state, record_published, refresh_kev


def catalog() -> dict[str, object]:
    return {
        "vulnerabilities": [
            {
                "cveID": "CVE-2026-1000",
                "dateAdded": "2026-07-24",
                "vendorProject": "Example Vendor",
                "product": "Example Product",
                "vulnerabilityName": "Example remote code execution",
                "requiredAction": "Apply the vendor update.",
            }
        ]
    }


def test_kev_alerts_include_action_and_source() -> None:
    alerts = kev_alerts(catalog(), since=date(2026, 7, 20), seen_ids=set())
    assert len(alerts) == 1
    assert alerts[0]["id"] == "hivesec-kev-cve-2026-1000"
    assert alerts[0]["schema_version"] == 1
    assert "Apply the vendor update." in alerts[0]["message"]
    assert KEV_URL in alerts[0]["message"]


def test_kev_alerts_do_not_repeat_seen_or_old_entries() -> None:
    assert not kev_alerts(catalog(), since=date(2026, 7, 25), seen_ids=set())
    assert not kev_alerts(
        catalog(), since=date(2026, 7, 20), seen_ids={"hivesec-kev-cve-2026-1000"}
    )


def test_refresh_persists_source_health_and_seen_ids(tmp_path: Path) -> None:
    class Response:
        status = 200

        def read(self) -> bytes:
            return json.dumps(catalog()).encode()

        def __enter__(self) -> Self:
            return self

        def __exit__(self, *_: object) -> None:
            return None

    state_path = tmp_path / "state.json"
    alerts, health = refresh_kev(
        state_path=state_path,
        user_agent="HiveSec-Sentinel-Test/1.0",
        opener=lambda *_args, **_kwargs: Response(),
    )
    state = load_state(state_path)
    assert health.status == "ok"
    assert len(alerts) == 1
    assert state["source_health"][0]["name"] == "CISA KEV"
    assert not state["seen_ids"]
    record_published(state_path, alerts)
    assert "hivesec-kev-cve-2026-1000" in load_state(state_path)["seen_ids"]


def test_refresh_without_bootstrap_applies_the_lookback_on_a_new_state(tmp_path: Path) -> None:
    """A missing state file must not publish the whole catalogue by default."""

    class Response:
        status = 200

        def read(self) -> bytes:
            return json.dumps(catalog()).encode()

        def __enter__(self) -> Self:
            return self

        def __exit__(self, *_: object) -> None:
            return None

    alerts, health = refresh_kev(
        state_path=tmp_path / "state.json",
        user_agent="HiveSec-Sentinel-Test/1.0",
        opener=lambda *_args, **_kwargs: Response(),
        bootstrap=False,
    )
    assert health.status == "ok"
    # The fixture entry is dated 2026-07-24, far outside any 1-30 day lookback.
    assert alerts == []
