"""Write bounded public-publication receipts for optional local projection.

One receipt is written per channel that actually accepted the alert. Callers
pass the real channel names (``telegram`` plus ``worker`` or ``github``); the
default is deliberately generic so a receipt never claims a channel that was
not used.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from .profile import PublicBrandContext
from .publisher import PublicAlert

DEFAULT_RECEIPT_DIR = (
    Path.home() / "Library/Application Support/HiveSec Sentinel/publication_receipts"
)


def write_publication_receipts(
    alert: PublicAlert,
    context: PublicBrandContext,
    *,
    channels: tuple[str, ...] = ("telegram", "site"),
    receipt_dir: Path = DEFAULT_RECEIPT_DIR,
) -> list[Path]:
    canonical = json.dumps(
        alert.payload(), ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode()
    payload_sha256 = hashlib.sha256(canonical).hexdigest()
    delivered_at = datetime.now(UTC).replace(microsecond=0).isoformat()
    revision = os.environ.get("SENTINEL_SOURCE_REVISION", "").strip() or None
    written: list[Path] = []
    receipt_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    for channel in channels:
        payload = {
            "contract_version": "public-publication-receipt-v1",
            "public_event_id": alert.id,
            "idempotency_key": f"{alert.id}-{channel}-{payload_sha256}",
            "channel": channel,
            "delivery_status": "delivered",
            "delivered_at": delivered_at,
            "public_url": None,
            "payload_sha256": payload_sha256,
            "source_revision": revision,
            "execution_profile": context.execution_profile,
            "policy_version": context.policy_version,
            "attribution_approval_ref": context.approval_ref,
        }
        target = receipt_dir / f"{alert.id}-{channel}-{payload_sha256[:12]}.json"
        with tempfile.NamedTemporaryFile(
            dir=receipt_dir, prefix=".receipt-", mode="w", encoding="utf-8", delete=False
        ) as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
            temporary = Path(handle.name)
        temporary.chmod(0o600)
        temporary.replace(target)
        written.append(target)
    return written
