"""Strictly public, credential-isolated HiveSec delivery adapters."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

_SECRET = re.compile(r"\b(?:github_pat_|ghp_|sk-|xai-)[A-Za-z0-9_-]{16,}\b")
_SEVERITIES = {"info", "warning", "critical"}
_ALERT_FIELDS = {
    "schema_version", "id", "title", "message", "severity", "source",
    "published_at",
}
_PRIVATE_FIELDS = {
    "victim", "email", "phone", "watchlist", "credential", "credentials",
    "private_outbox", "personal_data",
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
        required = (
            "schema_version",
            "id",
            "title",
            "message",
            "severity",
            "source",
            "published_at",
        )
        if any(not isinstance(value.get(key), str) for key in required[1:]):
            raise ValueError("public alert has missing or invalid fields")
        if value.get("schema_version") != 1 or value["source"] != "HiveSec Sentinel":
            raise ValueError("unsupported public alert contract")
        if value["severity"] not in _SEVERITIES or len(value["message"]) > 3500:
            raise ValueError("invalid public alert content")
        return cls(**{key: value[key] for key in required})

    def payload(self) -> dict[str, object]:
        return asdict(self)


def sanitize(text: str, *, maximum: int = 3500) -> str:
    return _SECRET.sub("[REDACTED]", "".join(c for c in text if c >= " " or c in "\n\t")).strip()[
        :maximum
    ]


class Publisher:
    """Deliver a PublicAlert to Telegram and to the BASH site.

    The site channel is one of:

    * **Worker intake** (preferred): ``POST intake_url`` on the ``bash-site``
      Cloudflare Worker, authenticated either with a shared secret in the
      ``X-HiveSec-Token`` header (current) or, if an Access intake application
      exists, with a Cloudflare Access *service token* (``CF-Access-Client-Id`` /
      ``CF-Access-Client-Secret``). The Worker validates the same contract and
      writes the public feed to KV.
    * **GitHub dispatch** (legacy): ``repository_dispatch`` ``security-alert`` at
      ``repository``; a GitHub Actions workflow validates and commits the feed.

    Configure exactly one. When both are configured the Worker intake wins.
    """

    def __init__(
        self,
        *,
        telegram_token: str,
        telegram_chat_id: str,
        user_agent: str,
        github_token: str = "",
        repository: str = "",
        intake_url: str = "",
        intake_token: str = "",
        intake_client_id: str = "",
        intake_client_secret: str = "",
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
        self.github_token, self.repository = github_token.strip(), repository.strip()

        if self.intake_url:
            if not self.intake_url.startswith("https://"):
                raise ValueError("intake_url must be https")
            has_token = bool(self.intake_token)
            has_service_token = bool(self.intake_client_id and self.intake_client_secret)
            if not (has_token or has_service_token):
                raise ValueError("HiveSec intake credentials are incomplete")
        elif self.github_token:
            owner, slash, name = self.repository.partition("/")
            if not slash or not owner or not name or "/" in name:
                raise ValueError("repository must use owner/name format")
        else:
            raise ValueError("HiveSec delivery credentials are incomplete")

    @classmethod
    def from_env(cls, environ, *, user_agent: str) -> Publisher:
        return cls(
            telegram_token=environ.get("HIVESEC_TELEGRAM_BOT_TOKEN", ""),
            telegram_chat_id=environ.get("HIVESEC_TELEGRAM_CHAT_ID", ""),
            github_token=environ.get("HIVESEC_GITHUB_TOKEN", ""),
            repository=environ.get("HIVESEC_GITHUB_REPOSITORY", "bashhive/bash-website"),
            intake_url=environ.get("HIVESEC_INTAKE_URL", ""),
            intake_token=environ.get("HIVESEC_INTAKE_TOKEN", ""),
            intake_client_id=environ.get("HIVESEC_CF_CLIENT_ID", ""),
            intake_client_secret=environ.get("HIVESEC_CF_CLIENT_SECRET", ""),
            user_agent=user_agent,
        )

    @property
    def site_channel(self) -> str:
        return "worker" if self.intake_url else "github"

    def publish(self, alert: PublicAlert) -> bool:
        alert = PublicAlert(
            **{
                **alert.payload(),
                "title": sanitize(alert.title, maximum=120),
                "message": sanitize(alert.message),
            }
        )
        return self._telegram(alert) and self._site(alert)

    def _site(self, alert: PublicAlert) -> bool:
        return self._worker(alert) if self.intake_url else self._github(alert)

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
        return self._request(request, expected=200)

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
        return self._request(request, expected=200)

    def _github(self, alert: PublicAlert) -> bool:
        request = Request(
            f"https://api.github.com/repos/{self.repository}/dispatches",
            data=json.dumps(
                {"event_type": "security-alert", "client_payload": alert.payload()}
            ).encode(),
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {self.github_token}",
                "Content-Type": "application/json",
                "User-Agent": self.user_agent,
            },
            method="POST",
        )
        return self._request(request, expected=204)

    def _request(self, request: Request, *, expected: int) -> bool:
        try:
            with self._opener(request, timeout=10) as response:  # nosec - fixed public endpoints
                return int(response.status) == expected
        except (HTTPError, URLError, TimeoutError, OSError):
            return False


def alert_from_input(value: object) -> PublicAlert:
    return PublicAlert.from_dict(value)
