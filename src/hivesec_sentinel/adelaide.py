"""Adelaide report writer: ``<repo>/.adelaide/report.json`` (contract version 1).

Adelaide reads only this file from the repository (contract described in
``/Users/raf/Code/adelaide/docs/REPO_REPORTS.md``); Sentinel keeps ownership of
``@hivesecsentinelbot``. The report is built from Sentinel's own local state
alone -- ``feed_state.json``, the Telegram publication receipts and a small
bounded cache of recently delivered alert titles -- and never touches the
network. It carries public KEV facts only.

Every public entry point here contains its own failures: a report problem logs
one line and never raises into the publishing pipeline.
"""

from __future__ import annotations

import json
import logging
import os
import re
import tempfile
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

from .publisher import sanitize
from .receipts import DEFAULT_RECEIPT_DIR

LOGGER = logging.getLogger(__name__)

REPO_DIR = Path(__file__).resolve().parents[2]
DEFAULT_REPORT_PATH = REPO_DIR / ".adelaide" / "report.json"
CACHE_NAME = "adelaide_cache.json"
BOT = "@hivesecsentinelbot"
SITE_URL = "https://hivesec.eu/sentinel"
NVD_URL = "https://nvd.nist.gov/vuln/detail/"

CACHE_MAX_ENTRIES = 50
CACHE_MAX_AGE = timedelta(days=7)
ALERT_WINDOW = timedelta(hours=48)
CHECK_MAX_AGE = timedelta(hours=12)
URGENT_WITHIN_DAYS = 7
MAX_ITEMS = 20
MAX_BYTES = 65536
TITLE_MAX = 200
SUMMARY_MAX = 400

_RANK = {"urgent": 0, "high": 1, "normal": 2, "low": 3}
_KEV_ID = re.compile(r"^hivesec-kev-(cve-\d{4}-\d{4,})$")
_SENTENCE_END = re.compile(r"(?<=[.!?])\s|\n")


def cache_path_for(state_path: Path) -> Path:
    """The cache lives next to the feed state file (the Sentinel state dir)."""
    return state_path.parent / CACHE_NAME


def _utc_now() -> datetime:
    return datetime.now(UTC).replace(microsecond=0)


def _parse_datetime(value: object) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _valid_date(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value.strip()[:10]).isoformat()
    except ValueError:
        return None


def _iso(moment: datetime | None) -> str:
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ") if moment else "never"


def cve_from_id(alert_id: object) -> str | None:
    match = _KEV_ID.match(alert_id) if isinstance(alert_id, str) else None
    return match.group(1).upper() if match else None


def alert_url(alert_id: object) -> str:
    cve = cve_from_id(alert_id)
    return f"{NVD_URL}{cve}" if cve else SITE_URL


def first_sentence(text: object) -> str:
    cleaned = sanitize(str(text or ""), maximum=4000)
    return _SENTENCE_END.split(cleaned, maxsplit=1)[0].strip()[:SUMMARY_MAX]


def _write_private_json(path: Path, value: object) -> None:
    """Atomic write: temp file in the same dir, 0600, then os.replace; dir 0700."""
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(path.parent, 0o700)
    descriptor, temporary = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    try:
        os.chmod(temporary, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.replace(temporary, path)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise


def load_cache(cache_path: Path) -> list[dict[str, Any]]:
    try:
        value = json.loads(cache_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    entries = value.get("entries") if isinstance(value, dict) else None
    return [entry for entry in entries or [] if isinstance(entry, dict)]


def _prune(entries: list[dict[str, Any]], now: datetime) -> list[dict[str, Any]]:
    kept = []
    for entry in entries:
        delivered = _parse_datetime(entry.get("delivered_at"))
        if delivered is not None and now - delivered <= CACHE_MAX_AGE:
            kept.append(entry)
    kept.sort(key=lambda entry: str(entry.get("delivered_at")))
    return kept[-CACHE_MAX_ENTRIES:]


def remember_delivered(
    cache_path: Path,
    alert: dict[str, object],
    due_date: object = None,
    *,
    now: datetime | None = None,
) -> None:
    """Keep the public title/summary/dueDate of a delivered alert for the report.

    ``feed_state.json`` keeps only IDs, so this bounded cache (max 50 entries,
    7 days, file mode 0600) is what gives the report readable titles.
    """
    try:
        moment = now or _utc_now()
        alert_id = str(alert.get("id") or "")
        if not alert_id:
            return
        entries = [e for e in load_cache(cache_path) if e.get("id") != alert_id]
        entries.append(
            {
                "id": alert_id,
                "title": sanitize(str(alert.get("title") or ""), maximum=TITLE_MAX),
                "summary": first_sentence(alert.get("message")),
                "due_date": _valid_date(due_date),
                "delivered_at": _iso(moment),
            }
        )
        _write_private_json(cache_path, {"version": 1, "entries": _prune(entries, moment)})
    except Exception as error:  # noqa: BLE001 - never raise into the publishing pipeline
        LOGGER.warning("adelaide cache not updated: %s", type(error).__name__)


def _receipt_deliveries(receipt_dir: Path, now: datetime) -> dict[str, datetime]:
    """Alert IDs accepted by Telegram within the window, from the local receipts."""
    delivered: dict[str, datetime] = {}
    if not receipt_dir.is_dir():
        return delivered
    horizon = (now - ALERT_WINDOW - timedelta(hours=1)).timestamp()
    for path in receipt_dir.glob("*.json"):
        try:
            if path.is_symlink() or path.stat().st_mtime < horizon:
                continue
            receipt = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if not isinstance(receipt, dict) or receipt.get("channel") != "telegram":
            continue
        alert_id = receipt.get("public_event_id")
        moment = _parse_datetime(receipt.get("delivered_at"))
        if not isinstance(alert_id, str) or moment is None:
            continue
        if now - moment <= ALERT_WINDOW and (
            alert_id not in delivered or moment > delivered[alert_id]
        ):
            delivered[alert_id] = moment
    return delivered


def _alert_items(
    cache: list[dict[str, Any]], receipts: dict[str, datetime], now: datetime
) -> list[tuple[dict[str, Any], datetime]]:
    by_id: dict[str, dict[str, Any]] = {}
    delivered = dict(receipts)
    for entry in cache:
        alert_id = entry.get("id")
        moment = _parse_datetime(entry.get("delivered_at"))
        if not isinstance(alert_id, str) or moment is None:
            continue
        by_id[alert_id] = entry
        if now - moment <= ALERT_WINDOW:
            delivered[alert_id] = max(moment, delivered.get(alert_id, moment))
    items = []
    for alert_id, moment in delivered.items():
        entry = by_id.get(alert_id, {})
        cve = cve_from_id(alert_id)
        title = sanitize(str(entry.get("title") or ""), maximum=TITLE_MAX) or (
            f"CISA KEV: {cve}" if cve else f"HiveSec Sentinel alert {alert_id}"
        )[:TITLE_MAX]
        summary = sanitize(str(entry.get("summary") or ""), maximum=SUMMARY_MAX) or (
            f"CISA has added {cve} to its Known Exploited Vulnerabilities catalog."
            if cve
            else "Public alert delivered to @hivesecsentinelbot."
        )
        due = _valid_date(entry.get("due_date"))
        urgent = due is not None and (
            date.fromisoformat(due) - now.date()
        ).days < URGENT_WITHIN_DAYS
        item = {
            "title": title,
            "priority": "urgent" if urgent else "high",
            "summary": summary[:SUMMARY_MAX],
            "url": alert_url(alert_id),
            "due_date": due,
            "kind": "alert",
        }
        items.append((item, moment))
    return items


def _status_item(state_path: Path, delivered_count: int, now: datetime) -> dict[str, Any]:
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        state = None
    if not isinstance(state, dict):
        return {
            "title": "KEV feed health: state unavailable",
            "priority": "high",
            "summary": "Sentinel feed state could not be read; the KEV refresh may not be running.",
            "url": SITE_URL,
            "due_date": None,
            "kind": "status",
        }
    health = state.get("source_health")
    first = health[0] if isinstance(health, list) and health and isinstance(health[0], dict) else {}
    status = str(first.get("status") or "unknown")
    checked = _parse_datetime(state.get("last_checked_at"))
    published = _parse_datetime(state.get("last_published_at"))
    stale = checked is None or now - checked > CHECK_MAX_AGE
    label = status if not stale or status != "ok" else "stale"
    summary = (
        f"CISA KEV source {status}; last checked {_iso(checked)}"
        f"{' (older than 12 h)' if stale else ''}; last published {_iso(published)}; "
        f"{delivered_count} alert(s) delivered to {BOT} in the last 48 h."
    )
    if status != "ok" and first.get("detail"):
        summary += f" Detail: {sanitize(str(first['detail']), maximum=160)}"
    return {
        "title": f"KEV feed health: {label}",
        "priority": "high" if stale or status != "ok" else "low",
        "summary": summary[:SUMMARY_MAX],
        "url": SITE_URL,
        "due_date": None,
        "kind": "status",
    }


def build_report(
    *,
    state_path: Path,
    cache_path: Path | None = None,
    receipt_dir: Path = DEFAULT_RECEIPT_DIR,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Build the contract-v1 report from local state only (no network)."""
    moment = now or _utc_now()
    cache = load_cache(cache_path or cache_path_for(state_path))
    alerts = _alert_items(cache, _receipt_deliveries(receipt_dir, moment), moment)
    alerts.sort(
        key=lambda pair: (
            _RANK[pair[0]["priority"]],
            pair[0]["due_date"] or "9999-12-31",
            -pair[1].timestamp(),
        )
    )
    status = _status_item(state_path, len(alerts), moment)
    items = [item for item, _ in alerts[: MAX_ITEMS - 1]]
    # Most important first; a degraded status leads the other high items.
    position = next(
        (
            index
            for index, item in enumerate(items)
            if _RANK[item["priority"]] >= _RANK[status["priority"]]
        ),
        len(items),
    )
    items.insert(position, status)
    return {
        "version": 1,
        "repo": "sentinel",
        "generated_at": _iso(moment),
        "bot": BOT,
        "items": items,
    }


def write_report(
    *,
    state_path: Path,
    report_path: Path = DEFAULT_REPORT_PATH,
    cache_path: Path | None = None,
    receipt_dir: Path = DEFAULT_RECEIPT_DIR,
    now: datetime | None = None,
) -> bool:
    """Write the report atomically (dir 0700, file 0600). Never raises."""
    try:
        report = build_report(
            state_path=state_path, cache_path=cache_path, receipt_dir=receipt_dir, now=now
        )
        while (
            len(json.dumps(report, ensure_ascii=False, indent=2).encode("utf-8")) + 1 > MAX_BYTES
            and len(report["items"]) > 1
        ):
            # Drop the least important non-status item until the file fits.
            victims = [i for i, item in enumerate(report["items"]) if item["kind"] != "status"]
            report["items"].pop(victims[-1])
        _write_private_json(report_path, report)
        return True
    except Exception as error:  # noqa: BLE001 - never raise into the publishing pipeline
        LOGGER.warning("adelaide report not written: %s", type(error).__name__)
        return False
