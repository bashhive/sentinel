# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

HiveSec Sentinel: the public cybersecurity-alert publisher for the BashHive brand. It is a small,
dependency-free Python 3.11+ package (`src/hivesec_sentinel`, ~500 lines) plus a macOS LaunchAgent
that polls the CISA KEV catalog every 6 hours and publishes new entries to Telegram
(`@hivesecsentinelbot`) and the BASH site (GitHub `repository_dispatch`).

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
.venv/bin/hivesec-sentinel refresh-kev --state /tmp/state.json --dry-run
```

There is no `requirements.txt`; CI (`.gitlab-ci.yml`) does `pip install -e .` then `pytest -q`.

## Required environment

`cli.main` calls `profile.resolve_public_brand(os.environ)` **before** parsing which subcommand
runs, so every invocation — including `--dry-run` — fails unless:

- `SENTINEL_EXECUTION_PROFILE=public_brand`
- `SENTINEL_POLICY_VERSION=execution-profiles-v1` (default if unset; any other value rejected)
- `SENTINEL_ATTRIBUTION_APPROVAL_REF=<3–160 chars>`
- `SENTINEL_USER_AGENT` optional (defaults to `HiveSec-Sentinel/1.0 (+https://hivesec.eu)`)

Live publishing additionally needs `HIVESEC_TELEGRAM_BOT_TOKEN`, `HIVESEC_TELEGRAM_CHAT_ID`,
`HIVESEC_GITHUB_TOKEN`, and optionally `HIVESEC_GITHUB_REPOSITORY` (default `bashhive/bash-website`).
`Publisher.__init__` raises if any of the three credentials is blank.

## Architecture

Data flow: `feeds.refresh_kev` → list of alert dicts → `publisher.alert_from_input` (strict
`PublicAlert` contract) → `Publisher.publish` (Telegram **then** GitHub dispatch) →
`receipts.write_publication_receipts` → `feeds.record_published` (marks IDs as seen).

Module responsibilities:

- `profile.py` — validates the execution-profile env contract into a frozen `PublicBrandContext`.
  This is the gate that makes every run explicit and attributable.
- `publisher.py` — `PublicAlert` is the versioned public contract (`schema_version` 1, exactly the
  seven fields in `_ALERT_FIELDS`, `source` must equal `"HiveSec Sentinel"`, severity in
  info/warning/critical, message ≤ 3500 chars). `from_dict` rejects **any** extra field, not just
  the `_PRIVATE_FIELDS` list — adding a field to the contract requires bumping `schema_version` and
  updating the BASH site receiver. `sanitize()` strips control chars and redacts token-shaped
  strings before delivery. `Publisher._request` swallows all network errors into `False`.
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
- `cli.py` — `publish <file>` (single alert) and `refresh-kev` (batch). Publication of a batch
  stops at the first failure and returns 1 without recording anything as seen.

Network is injected for testability: `feeds.fetch_json`/`refresh_kev` take an `opener` callable
(tests pass a lambda returning a fake response object), and `write_publication_receipts` takes a
`receipt_dir`. `Publisher.publish` hits real `urlopen` and is not covered by tests — don't add
tests that make live calls; add an injection point instead.

## Operations surface

- `scripts/refresh_public_feed.sh` (zsh) is what launchd runs: exports the SENTINEL_* env,
  verifies `.venv/bin/hivesec-sentinel` exists, pulls the three secrets from Keychain, then execs
  `refresh-kev --state "~/Library/Application Support/HiveSec Sentinel/feed_state.json"`.
- `config/launchd/com.hivesec.sentinel-feed-refresh.plist` — 21600 s interval, `RunAtLoad`; logs to
  `~/Library/Logs/HiveSecSentinel/`. Absolute paths to `/Users/raf/Code/sentinel` are hard-coded
  in both the plist and the script.
- `scripts/migrate_keychain_namespace.sh` — one-time copy from legacy `com.butler.hivesec.*`
  Keychain services to `com.hivesec.sentinel.*`.
- `docs/OPERATIONS.md` has the restart / inspect / recovery `launchctl` commands. Changing the
  state file layout means updating the recovery procedure there.

Changes to the runbooks, plist, or wrapper script affect a live scheduled job on this machine;
do not reload the LaunchAgent as a side effect of a code change.

## Branch note

Work happens on `codex/hivesec-feed-hardening`; `docs/ACTIVATION.md` records that this branch is
intentionally **not** merged to `main`. Don't merge or rebase onto `main` unless asked.
