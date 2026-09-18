# Activation

HiveSec Sentinel is activated from this repository, independently from any private assistant.
Adelaide reads only `.adelaide/report.json` (contract v1, /Users/raf/Code/adelaide/docs/REPO_REPORTS.md); this repo keeps ownership of its bot.

## Deployed state — 2026-07-26

The hardened publisher is committed as
`ef43d336448fd54f5dc98dda4fdb39b74a725687` on the review branch
`codex/hivesec-feed-hardening`. It has been pushed to local GitLab and verified
from a clean clone. That branch was merged into `main` on 18 Sep 2026; `main` is
now the default branch and what the LaunchAgent runs.

Sentinel remains the public publisher. It does not consume private scanner or
assistant payloads, and no public delivery is implied by repository deployment.
Every live publication still requires the `public_brand` profile, policy
version, and an explicit attribution approval reference.

The ecosystem-wide commit map, runtime health evidence, and restart procedure
are in the [SecurityWork deployment handoff](../../SecurityWork/docs/ecosystem/ECOSYSTEM_DEPLOYMENT_HANDOFF_2026-07-26.md).

## Configure

```bash
cd "/Users/raf/Code/sentinel"
uv sync --extra dev
```

The scheduled wrapper sources these from the git-ignored repository `.env`
(since commit 9c16c12; never commit it):

- `HIVESEC_TELEGRAM_BOT_TOKEN`
- `HIVESEC_TELEGRAM_CHAT_ID`

Only when `HIVESEC_SITE_DELIVERY=enabled`, the Worker intake credentials come
from Keychain (`com.hivesec.sentinel.intake-token`, else the
`com.hivesec.sentinel.cf-client-id` / `.cf-client-secret` pair). GitHub dispatch
and `HIVESEC_GITHUB_TOKEN` are retired.

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

Do not configure private-assistant or Data Breach Scanner credentials here. Deploy only after
`HIVESEC_TELEGRAM_BOT_TOKEN` and `HIVESEC_TELEGRAM_CHAT_ID` are present in the repository `.env`.

## Periodic source validation

`scripts/refresh_public_feed.sh` checks the official CISA Known Exploited Vulnerabilities
catalog every six hours. It keeps its delivery state under `~/Library/Application Support/HiveSec Sentinel/`
and reads the Telegram credentials from the repository `.env` at runtime; no secret is stored
in the script or plist. Keychain (`com.hivesec.sentinel.*` only) is read solely for the optional
Worker intake. The job records an alert as delivered as soon as Telegram accepts it
(`--record-on telegram`), so it is never sent twice.

## LaunchAgent

The macOS LaunchAgent wrapper now exports the required execution-profile variables before invoking the CLI:

- `SENTINEL_EXECUTION_PROFILE=public_brand`
- `SENTINEL_POLICY_VERSION=execution-profiles-v1`
- `SENTINEL_ATTRIBUTION_APPROVAL_REF=launchd-kev-refresh` (override if you need a different approval reference)
- `SENTINEL_USER_AGENT=HiveSec-Sentinel/1.0 (+https://hivesec.eu)`

Before enabling the agent, ensure the virtual environment exists and the package is installed:

```bash
cd /Users/raf/Code/sentinel
python3.11 -m venv .venv
. .venv/bin/activate
python -m pip install -U pip
python -m pip install -e '.[dev]'
```

The wrapper also fails fast with a clear error if `.venv/bin/hivesec-sentinel` is missing.
