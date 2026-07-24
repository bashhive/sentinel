from hivesec_sentinel.publisher import PublicAlert, alert_from_input, sanitize


def alert() -> dict[str, object]:
    return {
        "schema_version": 1,
        "id": "hivesec-example",
        "title": "CVE update",
        "message": "Atualizar sistemas.",
        "severity": "warning",
        "source": "HiveSec Sentinel",
        "published_at": "2026-07-23T12:00:00+00:00",
    }


def test_public_contract_rejects_private_identity() -> None:
    value = alert() | {"victim": "private@example.com"}
    try:
        alert_from_input(value)
    except ValueError:
        pass
    else:
        raise AssertionError("private data was accepted")


def test_public_contract_and_secret_redaction() -> None:
    parsed = alert_from_input(alert())
    assert isinstance(parsed, PublicAlert)
    assert sanitize("token github_pat_abcdefghijklmnopqrstuvwxyz") == "token [REDACTED]"
