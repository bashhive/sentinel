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
    def __init__(
        self,
        *,
        telegram_token: str,
        telegram_chat_id: str,
        github_token: str,
        repository: str,
        user_agent: str,
    ) -> None:
        if not all((telegram_token.strip(), telegram_chat_id.strip(), github_token.strip())):
            raise ValueError("HiveSec delivery credentials are incomplete")
        owner, slash, name = repository.partition("/")
        if not slash or not owner or not name or "/" in name:
            raise ValueError("repository must use owner/name format")
        self.telegram_token, self.telegram_chat_id = (
            telegram_token.strip(),
            telegram_chat_id.strip(),
        )
        self.github_token, self.repository = github_token.strip(), repository
        self.user_agent = user_agent

    def publish(self, alert: PublicAlert) -> bool:
        alert = PublicAlert(
            **{
                **alert.payload(),
                "title": sanitize(alert.title, maximum=120),
                "message": sanitize(alert.message),
            }
        )
        return self._telegram(alert) and self._github(alert)

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

    @staticmethod
    def _request(request: Request, *, expected: int) -> bool:
        try:
            with urlopen(request, timeout=10) as response:  # nosec - fixed public endpoints
                return int(response.status) == expected
        except (HTTPError, URLError, TimeoutError, OSError):
            return False


def alert_from_input(value: object) -> PublicAlert:
    return PublicAlert.from_dict(value)
