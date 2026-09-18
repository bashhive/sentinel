import pytest

from hivesec_sentinel.profile import POLICY_VERSION, resolve_public_brand


def test_public_brand_requires_explicit_profile_and_approval() -> None:
    with pytest.raises(ValueError, match="public_brand"):
        resolve_public_brand({})
    with pytest.raises(ValueError, match="approval"):
        resolve_public_brand({"SENTINEL_EXECUTION_PROFILE": "public_brand"})


def test_public_brand_context_is_versioned() -> None:
    context = resolve_public_brand(
        {
            "SENTINEL_EXECUTION_PROFILE": "public_brand",
            "SENTINEL_ATTRIBUTION_APPROVAL_REF": "PUBLIC-PUBLISH-2026-001",
        }
    )
    assert context.execution_profile == "public_brand"
    assert context.policy_version == POLICY_VERSION
    assert "HiveSec" in context.user_agent
