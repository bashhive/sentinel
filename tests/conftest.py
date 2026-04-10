"""
conftest.py — inject minimum env vars before any test imports config.
Prevents pydantic-settings from raising ValidationError on missing ANTHROPIC_API_KEY.
"""

import os
import pytest


def pytest_configure(config):
    """Set required env vars before collection starts."""
    os.environ.setdefault("ANTHROPIC_API_KEY", "test-key-placeholder")
    os.environ.setdefault("PROFILE", "aspasia_default")
    os.environ.setdefault("TELEGRAM_BOT_TOKEN", "")
