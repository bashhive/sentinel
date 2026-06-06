"""
conftest.py — inject minimum env vars before any test imports config.
Keeps pydantic-settings happy without requiring any real API key.
"""

import os
import pytest


def pytest_configure(config):
    """Set required env vars before collection starts."""
    os.environ.setdefault("LLM_PROVIDER", "groq")
    os.environ.setdefault("GROQ_API_KEY", "test-key-placeholder")
    os.environ.setdefault("PROFILE", "hivesec_default")
    os.environ.setdefault("TELEGRAM_BOT_TOKEN", "")
