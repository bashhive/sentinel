"""Sentinel's local adapter for the ecosystem execution-profile contract."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

POLICY_VERSION = "execution-profiles-v1"
PUBLIC_PROFILE = "public_brand"
DEFAULT_PUBLIC_USER_AGENT = "HiveSec-Sentinel/1.0 (+https://hivesec.eu)"


@dataclass(frozen=True, slots=True)
class PublicBrandContext:
    execution_profile: str
    policy_version: str
    approval_ref: str
    user_agent: str


def resolve_public_brand(env: Mapping[str, str]) -> PublicBrandContext:
    profile = env.get("SENTINEL_EXECUTION_PROFILE", "").strip()
    policy = env.get("SENTINEL_POLICY_VERSION", POLICY_VERSION).strip()
    approval = env.get("SENTINEL_ATTRIBUTION_APPROVAL_REF", "").strip()
    user_agent = env.get(
        "SENTINEL_USER_AGENT",
        DEFAULT_PUBLIC_USER_AGENT,
    ).strip()
    if profile != PUBLIC_PROFILE:
        raise ValueError("Sentinel live execution requires public_brand profile")
    if policy != POLICY_VERSION:
        raise ValueError("unsupported Sentinel execution policy version")
    if len(approval) < 3 or len(approval) > 160:
        raise ValueError("Sentinel attribution approval reference is required")
    if not user_agent or len(user_agent) > 200 or any(c in user_agent for c in "\r\n"):
        raise ValueError("invalid Sentinel public user-agent")
    return PublicBrandContext(profile, policy, approval, user_agent)
