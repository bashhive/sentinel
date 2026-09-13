from hivesec_sentinel.publisher import PublicAlert, alert_from_input, sanitize


def alert() -> dict[str, object]:
    return {
        "schema_version": 1,
        "id": "hivesec-example",
        "title": "CVE update",
        "message": "Update systems.",
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


def test_public_contract_rejects_unknown_fields() -> None:
    value = alert() | {"internal_note": "not public contract data"}
    try:
        alert_from_input(value)
    except ValueError:
        pass
    else:
        raise AssertionError("unknown public-contract data was accepted")


def test_public_contract_and_secret_redaction() -> None:
    parsed = alert_from_input(alert())
    assert isinstance(parsed, PublicAlert)
    assert sanitize("token github_pat_abcdefghijklmnopqrstuvwxyz") == "token [REDACTED]"


def test_public_contract_matches_worker_bounds_and_normalisation() -> None:
    value = alert() | {
        "id": "hivesec-CVE_2026.1",
        "title": "  title\x00 ",
        "message": "message\x00",
        "published_at": "2026-07-23T13:00:00+01:00",
    }
    parsed = alert_from_input(value)
    assert parsed.title == "title"
    assert parsed.message == "message"
    assert parsed.published_at == "2026-07-23T12:00:00+00:00"
    for invalid in (
        alert() | {"id": "not-hivesec"},
        alert() | {"published_at": "2026-07-23T12:00:00"},
        alert() | {"title": " "},
    ):
        try:
            alert_from_input(invalid)
        except ValueError:
            pass
        else:
            raise AssertionError("Worker-invalid public alert was accepted")


class _Response:
    def __init__(self, status: int) -> None:
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, *exc: object) -> None:
        return None


def _capture(status: int = 200):
    calls: list[object] = []

    def opener(request, timeout=10):
        calls.append(request)
        return _Response(status)

    return calls, opener


def test_worker_intake_channel_posts_with_service_token() -> None:
    from hivesec_sentinel.publisher import Publisher

    calls, opener = _capture(200)
    publisher = Publisher(
        telegram_token="t",
        telegram_chat_id="c",
        intake_url="https://hivesec.eu/api/sentinel/alert",
        intake_client_id="client-id",
        intake_client_secret="client-secret",
        user_agent="HiveSec-Sentinel/test",
        opener=opener,
    )
    assert publisher.site_channel == "worker"
    assert publisher.publish(alert_from_input(alert())) is True
    assert len(calls) == 2  # telegram, then worker intake
    intake = calls[1]
    assert intake.full_url == "https://hivesec.eu/api/sentinel/alert"
    assert intake.get_method() == "POST"
    assert intake.get_header("Cf-access-client-id") == "client-id"
    assert intake.get_header("Cf-access-client-secret") == "client-secret"
    body = intake.data.decode()
    assert '"source": "HiveSec Sentinel"' in body and '"victim"' not in body


def test_worker_intake_failure_is_reported_not_raised() -> None:
    from hivesec_sentinel.publisher import Publisher

    _, opener = _capture(403)
    publisher = Publisher(
        telegram_token="t",
        telegram_chat_id="c",
        intake_url="https://hivesec.eu/api/sentinel/alert",
        intake_client_id="client-id",
        intake_client_secret="client-secret",
        user_agent="HiveSec-Sentinel/test",
        opener=opener,
    )
    assert publisher.publish(alert_from_input(alert())) is False


def test_worker_intake_requires_https_and_full_credentials() -> None:
    from hivesec_sentinel.publisher import Publisher

    env = {
        "HIVESEC_TELEGRAM_BOT_TOKEN": "t",
        "HIVESEC_TELEGRAM_CHAT_ID": "c",
        "HIVESEC_SITE_DELIVERY": "enabled",
        "HIVESEC_INTAKE_URL": "https://hivesec.eu/api/sentinel/alert",
        "HIVESEC_CF_CLIENT_ID": "id",
        "HIVESEC_CF_CLIENT_SECRET": "secret",
    }
    assert Publisher.from_env(env, user_agent="ua").site_channel == "worker"
    for broken in (
        env | {"HIVESEC_INTAKE_URL": "http://hivesec.eu/api/sentinel/alert"},
        env | {"HIVESEC_CF_CLIENT_SECRET": ""},
        {k: v for k, v in env.items() if not k.startswith(("HIVESEC_INTAKE", "HIVESEC_CF"))},
    ):
        try:
            Publisher.from_env(broken, user_agent="ua")
        except ValueError:
            pass
        else:
            raise AssertionError("misconfigured publisher was accepted")


def test_shared_secret_intake_uses_token_header() -> None:
    from hivesec_sentinel.publisher import Publisher

    calls, opener = _capture(200)
    publisher = Publisher(
        telegram_token="t",
        telegram_chat_id="c",
        intake_url="https://hivesec.eu/api/sentinel/alert",
        intake_token="shared-secret-value",
        user_agent="HiveSec-Sentinel/test",
        opener=opener,
    )
    assert publisher.site_channel == "worker"
    assert publisher.publish(alert_from_input(alert())) is True
    intake = calls[1]
    assert intake.get_header("X-hivesec-token") == "shared-secret-value"
    assert intake.get_header("Cf-access-client-id") is None


def test_shared_secret_wins_over_service_token_and_is_required() -> None:
    from hivesec_sentinel.publisher import Publisher

    env = {
        "HIVESEC_TELEGRAM_BOT_TOKEN": "t",
        "HIVESEC_TELEGRAM_CHAT_ID": "c",
        "HIVESEC_SITE_DELIVERY": "enabled",
        "HIVESEC_INTAKE_URL": "https://hivesec.eu/api/sentinel/alert",
        "HIVESEC_INTAKE_TOKEN": "shared",
        "HIVESEC_CF_CLIENT_ID": "id",
        "HIVESEC_CF_CLIENT_SECRET": "secret",
    }
    _, opener = _capture(200)
    both = Publisher.from_env(env, user_agent="ua")
    both._opener = opener
    both.publish(alert_from_input(alert()))
    assert both.intake_token == "shared"

    bare = {
        k: v for k, v in env.items()
        if not k.startswith(("HIVESEC_INTAKE_TOKEN", "HIVESEC_CF"))
    }
    try:
        Publisher.from_env(bare, user_agent="ua")
    except ValueError:
        pass
    else:
        raise AssertionError("intake URL with no credentials was accepted")


def test_telegram_only_mode_needs_no_site_credentials() -> None:
    from hivesec_sentinel.publisher import Publisher

    calls, opener = _capture(200)
    publisher = Publisher.from_env(
        {
            "HIVESEC_TELEGRAM_BOT_TOKEN": "t",
            "HIVESEC_TELEGRAM_CHAT_ID": "c",
            "HIVESEC_SITE_DELIVERY": "disabled",
        },
        user_agent="ua",
    )
    publisher._opener = opener
    assert publisher.site_channel is None
    assert publisher.publish_detailed(alert_from_input(alert())) == {"telegram": True}
    assert len(calls) == 1
