"""Direct-source collection and freshness checks for public HiveSec alerts."""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

KEV_URL = "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"


@dataclass(frozen=True, slots=True)
class SourceHealth:
    name: str
    checked_at: str
    status: str
    detail: str

    def payload(self) -> dict[str, str]:
        return {
            "name": self.name,
            "checked_at": self.checked_at,
            "status": self.status,
            "detail": self.detail,
        }


def utc_now() -> datetime:
    return datetime.now(UTC).replace(microsecond=0)


def fetch_json(
    url: str,
    *,
    user_agent: str,
    opener: Callable[..., Any] = urlopen,
) -> dict[str, Any]:
    request = Request(
        url,
        headers={"Accept": "application/json", "User-Agent": user_agent},
    )
    with opener(request, timeout=20) as response:  # nosec - fixed official source URL
        if int(response.status) != 200:
            raise ValueError(f"source returned HTTP {response.status}")
        value = json.loads(response.read().decode("utf-8"))
    if not isinstance(value, dict):
        raise TypeError("source did not return a JSON object")
    return value


def load_state(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"schema_version": 1, "seen_ids": [], "source_health": []}
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or value.get("schema_version") != 1:
        raise ValueError("unsupported feed state")
    return value


def save_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def kev_alerts(
    catalog: dict[str, Any], *, since: date, seen_ids: set[str]
) -> list[dict[str, object]]:
    vulnerabilities = catalog.get("vulnerabilities")
    if not isinstance(vulnerabilities, list):
        raise TypeError("KEV catalog has no vulnerabilities list")
    alerts: list[dict[str, object]] = []
    for item in vulnerabilities:
        if not isinstance(item, dict):
            continue
        cve = item.get("cveID")
        date_added = item.get("dateAdded")
        if not isinstance(cve, str) or not isinstance(date_added, str):
            continue
        try:
            added = date.fromisoformat(date_added)
        except ValueError:
            continue
        alert_id = f"hivesec-kev-{cve.lower()}"
        if added < since or alert_id in seen_ids:
            continue
        name = str(item.get("vulnerabilityName") or cve).strip()
        vendor = str(item.get("vendorProject") or "Affected vendor").strip()
        product = str(item.get("product") or "affected product").strip()
        action = str(item.get("requiredAction") or "Apply the supplier mitigation.").strip()
        message = (
            f"CISA has added {cve} to its Known Exploited Vulnerabilities catalog. "
            f"Affected: {vendor} {product}. Recommended action: {action}\n\n"
            f"Source: {KEV_URL}"
        )
        alerts.append(
            {
                "schema_version": 1,
                "id": alert_id,
                "title": f"CISA KEV: {name}",
                "message": message,
                "severity": "critical",
                "source": "HiveSec Sentinel",
                "published_at": f"{date_added}T00:00:00+00:00",
            }
        )
    return alerts


def refresh_kev(
    *,
    state_path: Path,
    user_agent: str,
    lookback_days: int = 7,
    opener: Callable[..., Any] = urlopen,
) -> tuple[list[dict[str, object]], SourceHealth]:
    now = utc_now()
    state = load_state(state_path)
    prior_seen = {item for item in state.get("seen_ids", []) if isinstance(item, str)}
    default_since = (now - timedelta(days=lookback_days)).date()

    if not state_path.is_file() and not prior_seen:
        since = date.min
    else:
        since = default_since

    try:
        catalog = fetch_json(KEV_URL, user_agent=user_agent, opener=opener)
        alerts = kev_alerts(catalog, since=since, seen_ids=prior_seen)
        health = SourceHealth(
            "CISA KEV",
            now.isoformat(),
            "ok",
            f"{len(alerts)} new eligible entries; old and seen alerts suppressed",
        )
    except (OSError, TypeError, ValueError, json.JSONDecodeError) as error:
        health = SourceHealth("CISA KEV", now.isoformat(), "error", str(error)[:160])
        alerts = []
    state["source_health"] = [health.payload()]
    state["last_checked_at"] = now.isoformat()
    save_state(state_path, state)
    return alerts, health


def record_published(state_path: Path, alerts: list[dict[str, object]]) -> None:
    """Record alert delivery only after all public channels accepted it."""
    state = load_state(state_path)
    seen = {item for item in state.get("seen_ids", []) if isinstance(item, str)}
    for alert in alerts:
        alert_id = alert.get("id")
        if isinstance(alert_id, str) and alert_id:
            seen.add(alert_id)
    state["seen_ids"] = sorted(seen)
    state["last_published_at"] = utc_now().isoformat()
    save_state(state_path, state)
