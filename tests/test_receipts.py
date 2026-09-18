import json
from pathlib import Path

from hivesec_sentinel.profile import PublicBrandContext
from hivesec_sentinel.publisher import PublicAlert
from hivesec_sentinel.receipts import write_publication_receipts


def test_receipts_are_public_bounded_and_profile_aware(tmp_path: Path) -> None:
    alert = PublicAlert(
        schema_version=1,
        id="hivesec-example",
        title="CVE update",
        message="Update systems.",
        severity="warning",
        source="HiveSec Sentinel",
        published_at="2026-07-23T12:00:00+00:00",
    )
    context = PublicBrandContext(
        execution_profile="public_brand",
        policy_version="execution-profiles-v1",
        approval_ref="PUBLIC-PUBLISH-2026-001",
        user_agent="HiveSec-Sentinel-Test/1.0",
    )
    paths = write_publication_receipts(alert, context, receipt_dir=tmp_path)
    assert len(paths) == 2
    receipt = json.loads(paths[0].read_text())
    assert receipt["execution_profile"] == "public_brand"
    assert receipt["payload_sha256"]
    assert "message" not in receipt
    assert "title" not in receipt
