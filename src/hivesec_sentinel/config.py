"""Runtime configuration with macOS Keychain support."""

from __future__ import annotations

import os
import platform
import subprocess
from dataclasses import dataclass
from pathlib import Path


def _default_data_dir() -> Path:
    return Path.home() / "Library" / "Application Support" / "HiveSec Sentinel"


def _default_scanner_outbox() -> Path:
    return Path.home() / "Library" / "Application Support" / "Data Breach Scanner" / "outbox"


def keychain_value(service: str, account: str) -> str:
    if platform.system() != "Darwin":
        return ""
    try:
        result = subprocess.run(
            [
                "/usr/bin/security",
                "find-generic-password",
                "-s",
                service,
                "-a",
                account,
                "-w",
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=3,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    return result.stdout.strip() if result.returncode == 0 else ""


@dataclass(frozen=True, slots=True)
class Settings:
    data_dir: Path = _default_data_dir()
    scanner_outbox_root: Path = _default_scanner_outbox()
    log_level: str = "INFO"
    grok_base_url: str = "https://api.x.ai/v1"
    grok_model: str = "grok-4.3"
    xai_api_key: str = ""
    telegram_bot_username: str = "hivesecsentinelbot"
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    github_repository: str = "rafpt/bash-site"
    github_token: str = ""
    timeout_seconds: float = 20.0
    max_event_bytes: int = 64 * 1024

    @property
    def state_path(self) -> Path:
        return self.data_dir / "state.json"

    @property
    def configured(self) -> bool:
        return bool(
            self.xai_api_key
            and self.telegram_bot_token
            and self.telegram_chat_id
            and self.github_repository
            and self.github_token
        )

    @classmethod
    def from_env(cls) -> Settings:
        return cls(
            data_dir=Path(os.getenv("HIVESEC_DATA_DIR", str(_default_data_dir()))).expanduser(),
            scanner_outbox_root=Path(
                os.getenv("HIVESEC_SCANNER_OUTBOX_ROOT", str(_default_scanner_outbox()))
            ).expanduser(),
            log_level=os.getenv("HIVESEC_LOG_LEVEL", "INFO").upper(),
            grok_base_url=os.getenv("HIVESEC_GROK_BASE_URL", "https://api.x.ai/v1").rstrip("/"),
            grok_model=os.getenv("HIVESEC_GROK_MODEL", "grok-4.3"),
            xai_api_key=os.getenv("HIVESEC_XAI_API_KEY")
            or keychain_value("com.hivesec.xai", "api-key"),
            telegram_bot_username=os.getenv(
                "HIVESEC_TELEGRAM_BOT_USERNAME", "hivesecsentinelbot"
            ).removeprefix("@"),
            telegram_bot_token=os.getenv("HIVESEC_TELEGRAM_BOT_TOKEN")
            or keychain_value("com.hivesec.telegram", "bot-token"),
            telegram_chat_id=os.getenv("HIVESEC_TELEGRAM_CHAT_ID")
            or keychain_value("com.hivesec.telegram", "chat-id"),
            github_repository=os.getenv("HIVESEC_GITHUB_REPOSITORY", "rafpt/bash-site"),
            github_token=os.getenv("HIVESEC_GITHUB_TOKEN")
            or keychain_value("com.hivesec.github", "token"),
            timeout_seconds=float(os.getenv("HIVESEC_TIMEOUT_SECONDS", "20")),
            max_event_bytes=int(os.getenv("HIVESEC_MAX_EVENT_BYTES", str(64 * 1024))),
        )
