# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

HiveSec Sentinel: the public cybersecurity-alert publisher for the BashHive brand. It is a small,
dependency-free Python 3.11+ package (`src/hivesec_sentinel`, ~500 lines) plus a macOS LaunchAgent
that polls the CISA KEV catalog every 6 hours and publishes new entries to Telegram
(`@hivesecsentinelbot`) and the BashHive site.

**Read this before assuming what runs where (13 Sep 2026).** The site feed is now collected
*inside Cloudflare*: `bash-website/src/kev.js` runs on a Worker Cron Trigger every 10 minutes and
is a port of `feeds.py:kev_alerts()` from this repo — same ids, same titles, same wording, so the
two paths dedupe against each other. This machine is no longer the thing that keeps the public
feed alive; the 6-hourly LaunchAgent froze the feed whenever the Mac slept, which is why the
collector moved. What this repository still owns exclusively is **Telegram** delivery and any
alert that does not come from KEV.

**The site channel is currently blocked.** Cloudflare Access fronts every path of all six BashHive
hostnames, so `POST /api/sentinel/alert` answers 302 — the edge does not know `X-HiveSec-Token`.
Measured with the live Keychain token on 13 Sep 2026. Telegram is unaffected. See
`docs/ARCHITECTURE.md` and `bash-website/CUTOVER_ACCESS_LOGIN_20260909.md` §T.

`AGENTS.md` holds the binding repository rules and is imported here verbatim:

@AGENTS.md

In practice those rules mean: no code path may accept victim, watchlist, personal-contact,
credential, or private-outbox data; no active scanning or personal monitoring (authoritative
public feeds like CISA KEV are fine); credentials reach the process only as `HIVESEC_*` env vars
read from the `com.hivesec.sentinel.*` Keychain namespace at runtime; and every live run needs the
`public_brand` profile plus an attribution approval ref (see "Required environment").

## Commands

The repo venv at `.venv` is the canonical interpreter (the LaunchAgent wrapper depends on it).
`docs/ACTIVATION.md` also shows `uv sync --extra dev` / `uv run ...`; either works, but
`AGENTS.md` names `.venv/bin/python -m pytest` as the test gate.

```bash
# one-time setup
python3.11 -m venv .venv && .venv/bin/python -m pip install -e '.[dev]'

# test gate (required before reporting completion)
.venv/bin/python -m pytest -q
.venv/bin/python -m pytest tests/test_feeds.py -q                  # one file
.venv/bin/python -m pytest tests/test_feeds.py::test_kev_alerts_include_action_and_source  # one test

# lint (ruff, line-length 100, py311 target)
.venv/bin/ruff check src tests

# CLI dry runs (need the SENTINEL_* env below; no HIVESEC_* credentials needed for --dry-run)
.venv/bin/hivesec-sentinel publish alert.json --dry-run
.venv/bin/hivesec-sentinel refresh-kev --state /tmp/state.json --lookback-days 7 --dry-run
```

`refresh-kev` defaults to `--state data/feed_state.json` (`data/` is gitignored) and
`--lookback-days 7` (accepted range 1–30). It exits 1 whenever KEV source health is not `ok`,
even with `--dry-run`, so a failed fetch looks like a failed run.

There is no `requirements.txt`; CI (`.gitlab-ci.yml`, python:3.12 image) does `pip install -e .`
(no `[dev]` extras) then `pytest -q`.

## Required environment

`cli.main` calls `profile.resolve_public_brand(os.environ)` right after argparse and before any
subcommand logic, so every invocation — including `--dry-run` — fails unless:

- `SENTINEL_EXECUTION_PROFILE=public_brand`
- `SENTINEL_POLICY_VERSION=execution-profiles-v1` (default if unset; any other value rejected)
- `SENTINEL_ATTRIBUTION_APPROVAL_REF=<3–160 chars>`
- `SENTINEL_USER_AGENT` optional (defaults to `HiveSec-Sentinel/1.0 (+https://hivesec.eu)`)
- `SENTINEL_SOURCE_REVISION` optional; if set it is copied into each receipt as `source_revision`

Live publishing additionally needs `HIVESEC_TELEGRAM_BOT_TOKEN`, `HIVESEC_TELEGRAM_CHAT_ID` and ONE
site channel (`Publisher.from_env` picks it; `__init__` raises if neither is complete):

- **Worker intake, shared secret** (what the live job uses): `HIVESEC_INTAKE_URL` (wrapper
  default `https://hivesec.eu/api/sentinel/alert`) and `HIVESEC_INTAKE_TOKEN`, Keychain item
  `com.hivesec.sentinel.intake-token`, sent as the `X-HiveSec-Token` header and compared by the
  Worker against its `INTAKE_SECRET` as SHA-256 digests. Expected response: HTTP 200.
- **Worker intake, Access service token**: `HIVESEC_CF_CLIENT_ID` / `HIVESEC_CF_CLIENT_SECRET`,
  Keychain items `com.hivesec.sentinel.cf-client-id` / `.cf-client-secret`. **Not configured on
  this machine** (checked 13 Sep 2026) — and it is what an Access Service Auth application would
  need, so this is the channel to restore rather than the shared secret.
- **GitHub dispatch** (legacy, effectively dead): `HIVESEC_GITHUB_TOKEN`, optionally
  `HIVESEC_GITHUB_REPOSITORY` (default `bashhive/bash-website`). Expected response: HTTP 204. It
  reached the old GitHub Pages feed, which no longer serves anything. **Treat a fallback to
  GitHub as an outage, not as redundancy.**

The wrapper picks the first channel whose Keychain items exist, in that order. Both the shared
secret and the GitHub token are present on this machine; the Access pair is not.

## Architecture

Data flow: `feeds.refresh_kev` → list of alert dicts → `publisher.alert_from_input` (strict
`PublicAlert` contract) → `Publisher.publish` (Telegram **then** the site channel) →
`receipts.write_publication_receipts` → `feeds.record_published` (marks IDs as seen).

Module responsibilities:

- `profile.py` — validates the execution-profile env contract into a frozen `PublicBrandContext`.
  This is the gate that makes every run explicit and attributable.
- `publisher.py` — `PublicAlert` is the versioned public contract (`schema_version` 1, exactly the
  seven fields in `_ALERT_FIELDS`, `source` must equal `"HiveSec Sentinel"`, severity in
  info/warning/critical, message ≤ 3500 chars). `from_dict` rejects **any** extra field, not just
  the `_PRIVATE_FIELDS` list — adding a field to the contract requires bumping `schema_version` and
  updating the BASH site receiver. `sanitize()` strips control chars and redacts token-shaped
  strings before delivery (title capped at 120 chars). `Publisher._request` swallows all network
  errors into `False`. The GitHub call is `repository_dispatch` with `event_type: security-alert`
  and the alert payload as `client_payload`; the receiving site repo is `bashhive/bash-website`
  (local checkout `/Users/raf/Code/BASH_site/public_html` per README), so contract changes must
  land there too.
- `feeds.py` — KEV collection and the delivery-state file (`schema_version: 1`, `seen_ids`,
  `source_health`). `refresh_kev` only *reads* `seen_ids` and writes health; IDs are added to
  `seen_ids` by `record_published`, which the CLI calls **only after every alert in the batch was
  accepted by both channels**. This is the duplicate-suppression invariant — keep it. On a
  brand-new state file the lookback is ignored (`since = date.min`) so the first run publishes the
  whole catalog; the runbook expects a manual review of that first batch.
- `receipts.py` — writes one bounded JSON receipt per channel to
  `~/Library/Application Support/HiveSec Sentinel/publication_receipts/` (0700 dir, 0600 files,
  atomic rename). Receipts deliberately contain the payload SHA-256 and profile metadata but
  **not** the alert title/message; tests assert this.
- `cli.py` — `publish <file>` (single alert; never touches the state file) and `refresh-kev`
  (batch). Publication of a batch stops at the first failure and returns 1 without recording
  anything as seen. Consequence: alerts delivered earlier in that same batch already have
  receipts but are **not** in `seen_ids`, so the next run re-sends them. This is the accepted
  trade-off (at-least-once delivery); don't "fix" it by recording per-alert without discussion.

Network is injected for testability: `feeds.fetch_json`/`refresh_kev` take an `opener` callable
(tests pass a lambda returning a fake response object), and `write_publication_receipts` takes a
`receipt_dir`. `Publisher` takes an `opener` (defaults to `urlopen`); `tests/test_publisher.py` injects a fake
and asserts the request shape — never make live calls from tests.

## Operations surface

- `scripts/refresh_public_feed.sh` (zsh) is what launchd runs: exports the SENTINEL_* env with
  `${VAR:-default}` fallbacks, verifies `.venv/bin/hivesec-sentinel` exists (and pip-installs
  `.[dev]` into the venv if it is missing), pulls the three secrets from Keychain
  (`com.hivesec.sentinel.telegram`, `.telegram-chat-id`, `.github`), then execs
  `refresh-kev --state "~/Library/Application Support/HiveSec Sentinel/feed_state.json"
  --lookback-days "${SENTINEL_LOOKBACK_DAYS:-7}"`.
- `config/launchd/com.hivesec.sentinel-feed-refresh.plist` — 21600 s interval, `RunAtLoad`; logs to
  `~/Library/Logs/HiveSecSentinel/`. Absolute paths to `/Users/raf/Code/sentinel` are hard-coded
  in both the plist and the script. The plist's `EnvironmentVariables` win over the script's
  defaults, so the live attribution ref is `PUBLIC-PUBLISH-2026-001` from the plist, not the
  `launchd-kev-refresh` fallback that the script and `docs/ACTIVATION.md` mention.
- `scripts/migrate_keychain_namespace.sh` — one-time copy from legacy `com.butler.hivesec.*`
  Keychain services to `com.hivesec.sentinel.*`.
- `docs/OPERATIONS.md` has the restart / inspect / recovery `launchctl` commands. Changing the
  state file layout means updating the recovery procedure there.

Changes to the runbooks, plist, or wrapper script affect a live scheduled job on this machine;
do not reload the LaunchAgent as a side effect of a code change.

## Branch note

Work happens on `codex/hivesec-feed-hardening`; `docs/ACTIVATION.md` records that this branch is
intentionally **not** merged to `main`. Don't merge or rebase onto `main` unless asked.
