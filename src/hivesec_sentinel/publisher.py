"""Strictly public, credential-isolated HiveSec delivery adapters."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

logger = logging.getLogger("hivesec_sentinel.publisher")

_SECRET = re.compile(r"\b(?:github_pat_|ghp_|sk-|xai-)[A-Za-z0-9_-]{16,}\b")
_SEVERITIES = {"info", "warning", "critical"}
_SAFE_ID = re.compile(r"^[A-Za-z0-9._-]{1,80}$")
_ISO_TZ = re.compile(r"(?:Z|[+-]\d{2}:?\d{2})$", re.IGNORECASE)
_ALERT_FIELDS = {
    "schema_version",
    "id",
    "title",
    "message",
    "severity",
    "source",
    "published_at",
}
_PRIVATE_FIELDS = {
    "victim",
    "email",
    "phone",
    "watchlist",
    "credential",
    "credentials",
    "private_outbox",
    "personal_data",
}


@dataclass(frozen=True, slots=True)
class PublicAlert:
    schema_version: int
    id: str
    title: str
    message: str
    severity: str
    source: str
    published_at: str

    @classmethod
    def from_dict(cls, value: object) -> PublicAlert:
        if not isinstance(value, dict):
            raise TypeError("public alert must be an object")
        if set(value) != _ALERT_FIELDS or set(value) & _PRIVATE_FIELDS:
            raise ValueError("public alert must be an object without private identity")
        if value.get("schema_version") != 1 or isinstance(value.get("schema_version"), bool):
            raise ValueError("unsupported public alert contract")
        if any(not isinstance(value.get(key), str) for key in _ALERT_FIELDS - {"schema_version"}):
            raise ValueError("public alert has missing or invalid fields")
        if not value["id"].startswith("hivesec-") or not _SAFE_ID.fullmatch(value["id"]):
            raise ValueError("invalid public alert ID")
        if value["severity"] not in _SEVERITIES:
            raise ValueError("invalid public alert severity")
        source = _clean_text(value["source"], maximum=80)
        if source != "HiveSec Sentinel":
            raise ValueError("unsupported public alert contract")
        return cls(
            schema_version=1,
            id=value["id"],
            title=_clean_text(value["title"], maximum=160),
            message=_clean_text(value["message"], maximum=6000),
            severity=value["severity"],
            source=source,
            published_at=_normalise_published_at(value["published_at"]),
        )

    def payload(self) -> dict[str, object]:
        return asdict(self)


def sanitize(text: str, *, maximum: int = 3500) -> str:
    return _SECRET.sub("[REDACTED]", "".join(c for c in text if c >= " " or c in "\n\t")).strip()[
        :maximum
    ]


def _clean_text(value: str, *, maximum: int) -> str:
    cleaned = "".join(char for char in value.strip() if char >= " " or char in "\n\t")
    if not cleaned:
        raise ValueError("public alert text cannot be empty")
    return cleaned[:maximum]


def _normalise_published_at(value: str) -> str:
    timestamp = _clean_text(value, maximum=40)
    if not _ISO_TZ.search(timestamp):
        raise ValueError("public alert timestamp must include a timezone")
    try:
        parsed = datetime.fromisoformat(timestamp)
    except ValueError as error:
        raise ValueError("invalid public alert timestamp") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("public alert timestamp must include a timezone")
    return parsed.astimezone(UTC).replace(microsecond=0).isoformat()


class Publisher:
    """Deliver a PublicAlert to Telegram and to the BASH site.

    The site channel is one of:

    * **Worker intake** (preferred): ``POST intake_url`` on the ``bash-site``
      Cloudflare Worker, authenticated either with a shared secret in the
      ``X-HiveSec-Token`` header (current) or, if an Access intake application
      exists, with a Cloudflare Access *service token* (``CF-Access-Client-Id`` /
      ``CF-Access-Client-Secret``). The Worker validates the same contract and
      writes the public feed to KV.
    Site delivery is disabled for the scheduled job by default because the
    Worker cron owns routine site collection. When an operator enables it, the
    only supported site channel is the authenticated Worker intake.
    """

    def __init__(
        self,
        *,
        telegram_token: str,
        telegram_chat_id: str,
        user_agent: str,
        intake_url: str = "",
        intake_token: str = "",
        intake_client_id: str = "",
        intake_client_secret: str = "",
        site_delivery: bool = True,
        opener=urlopen,
    ) -> None:
        if not all((telegram_token.strip(), telegram_chat_id.strip())):
            raise ValueError("HiveSec delivery credentials are incomplete")
        self.telegram_token, self.telegram_chat_id = (
            telegram_token.strip(),
            telegram_chat_id.strip(),
        )
        self.user_agent = user_agent
        self._opener = opener

        self.intake_url = intake_url.strip()
        self.intake_token = intake_token.strip()
        self.intake_client_id = intake_client_id.strip()
        self.intake_client_secret = intake_client_secret.strip()
        self.site_delivery = site_delivery

        if not self.site_delivery:
            return
        if self.intake_url:
            if not self.intake_url.startswith("https://"):
                raise ValueError("intake_url must be https")
            has_token = bool(self.intake_token)
            has_service_token = bool(self.intake_client_id and self.intake_client_secret)
            if not (has_token or has_service_token):
                raise ValueError("HiveSec intake credentials are incomplete")
        else:
            raise ValueError("HiveSec Worker intake URL is required when site delivery is enabled")

    @classmethod
    def from_env(cls, environ, *, user_agent: str) -> Publisher:
        delivery = environ.get("HIVESEC_SITE_DELIVERY", "disabled").strip().lower()
        if delivery not in {"enabled", "disabled"}:
            raise ValueError("HIVESEC_SITE_DELIVERY must be enabled or disabled")
        return cls(
            telegram_token=environ.get("HIVESEC_TELEGRAM_BOT_TOKEN", ""),
            telegram_chat_id=environ.get("HIVESEC_TELEGRAM_CHAT_ID", ""),
            intake_url=environ.get("HIVESEC_INTAKE_URL", ""),
            intake_token=environ.get("HIVESEC_INTAKE_TOKEN", ""),
            intake_client_id=environ.get("HIVESEC_CF_CLIENT_ID", ""),
            intake_client_secret=environ.get("HIVESEC_CF_CLIENT_SECRET", ""),
            site_delivery=delivery == "enabled",
            user_agent=user_agent,
        )

    @property
    def site_channel(self) -> str | None:
        if not self.site_delivery:
            return None
        return "worker"

    def publish(self, alert: PublicAlert) -> bool:
        """Deliver to every configured channel; True only if all accepted."""
        return all(self.publish_detailed(alert).values())

    def publish_detailed(self, alert: PublicAlert) -> dict[str, bool]:
        """Per-channel delivery outcome, e.g. ``{"telegram": True, "worker": False}``.

        Telegram is attempted first and the site channel second, as before. The
        caller decides what a partial success means: a channel that accepted the
        alert must not be re-sent on the next run just because another failed.
        """
        alert = PublicAlert(
            **{
                **alert.payload(),
                "title": sanitize(alert.title, maximum=120),
                "message": sanitize(alert.message),
            }
        )
        outcomes = {"telegram": self._telegram(alert)}
        if self.site_delivery:
            outcomes[self.site_channel or "site"] = self._site(alert)
        return outcomes

    def _site(self, alert: PublicAlert) -> bool:
        return self._worker(alert)

    def _worker(self, alert: PublicAlert) -> bool:
        # Shared secret (current) or Cloudflare Access service token (dormant).
        if self.intake_token:
            auth = {"X-HiveSec-Token": self.intake_token}
        else:
            auth = {
                "CF-Access-Client-Id": self.intake_client_id,
                "CF-Access-Client-Secret": self.intake_client_secret,
            }
        request = Request(
            self.intake_url,
            data=json.dumps(alert.payload()).encode(),
            headers={
                **auth,
                "Content-Type": "application/json",
                "User-Agent": self.user_agent,
            },
            method="POST",
        )
        return self._request(request, expected=200, channel="worker")

    def _telegram(self, alert: PublicAlert) -> bool:
        request = Request(
            f"https://api.telegram.org/bot{self.telegram_token}/sendMessage",
            data=json.dumps(
                {
                    "chat_id": self.telegram_chat_id,
                    "text": f"{alert.title}\n\n{alert.message}",
                    "disable_web_page_preview": True,
                }
            ).encode(),
            headers={"Content-Type": "application/json", "User-Agent": self.user_agent},
            method="POST",
        )
        return self._request(request, expected=200, channel="telegram")

    def _request(self, request: Request, *, expected: int, channel: str = "") -> bool:
        """Perform one delivery call.

        Failures are still contained (the caller gets False, never an
        exception), but they are no longer silent: every non-expected status
        and every transport error is logged with the channel, the host and the
        reason, so a blocked intake (302), a revoked token (401) and a DNS
        failure are distinguishable in the LaunchAgent log.
        """
        host = request.host or request.full_url
        try:
            with self._opener(request, timeout=10) as response:  # nosec - fixed public endpoints
                status = int(response.status)
        except HTTPError as error:
            logger.warning(
                "delivery failed: channel=%s host=%s status=%s reason=http_error",
                channel,
                host,
                error.code,
            )
            return False
        except (URLError, TimeoutError, OSError) as error:
            logger.warning(
                "delivery failed: channel=%s host=%s reason=%s detail=%.120s",
                channel,
                host,
                type(error).__name__,
                error,
            )
            return False
        if status != expected:
            logger.warning(
                "delivery rejected: channel=%s host=%s status=%s expected=%s",
                channel,
                host,
                status,
                expected,
            )
            return False
        logger.info("delivery accepted: channel=%s host=%s status=%s", channel, host, status)
        return True


def alert_from_input(value: object) -> PublicAlert:
    return PublicAlert.from_dict(value)
