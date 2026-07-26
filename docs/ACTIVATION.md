# Activation

HiveSec Sentinel is activated from this repository, independently from Butler.

## Deployed state — 2026-07-26

The hardened publisher is committed as
`ef43d336448fd54f5dc98dda4fdb39b74a725687` on the review branch
`codex/hivesec-feed-hardening`. It has been pushed to local GitLab and verified
from a clean clone. The branch is intentionally not merged to `main` here.

Sentinel remains the public publisher. It does not consume private scanner or
Butler payloads, and no public delivery is implied by repository deployment.
Every live publication still requires the `public_brand` profile, policy
version, and an explicit attribution approval reference.

The ecosystem-wide commit map, runtime health evidence, and restart procedure
are in the [SecurityWork deployment handoff](../../SecurityWork/docs/ecosystem/ECOSYSTEM_DEPLOYMENT_HANDOFF_2026-07-26.md).

## Configure

```bash
cd "/Users/raf/Code/sentinel"
uv sync --extra dev
```

The approved secret store supplies dedicated credentials for:

- `HIVESEC_TELEGRAM_BOT_TOKEN`
- `HIVESEC_TELEGRAM_CHAT_ID`
- `HIVESEC_GITHUB_TOKEN`

Every live or dry-run invocation also requires:

- `SENTINEL_EXECUTION_PROFILE=public_brand`
- `SENTINEL_POLICY_VERSION=execution-profiles-v1`
- `SENTINEL_ATTRIBUTION_APPROVAL_REF=<approved change or policy reference>`

## Validate

```bash
cd "/Users/raf/Code/sentinel"
uv run pytest
uv run hivesec-sentinel publish alert.json --dry-run
```

## Do not install

Do not configure Butler or Data Breach Scanner credentials here. Deploy only after the public
site has supplied `HIVESEC_TELEGRAM_BOT_TOKEN`, `HIVESEC_TELEGRAM_CHAT_ID` and
`HIVESEC_GITHUB_TOKEN` through its approved secret store.

## Periodic source validation

`scripts/refresh_public_feed.sh` checks the official CISA Known Exploited Vulnerabilities
catalog every six hours. It keeps its delivery state under `~/Library/Application Support/HiveSec Sentinel/`
and retrieves credentials from Keychain at runtime; no secret is stored in the script or plist.

The refresh script uses only `com.hivesec.sentinel.*` Keychain entries. Run the
one-time namespace migration script before installing the LaunchAgent. The job publishes a new alert only
after both Telegram and the public-site dispatch succeed, then records it as delivered to prevent
duplicates.
