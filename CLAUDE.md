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

**The optional site channel is currently blocked.** Cloudflare Access fronts every path of all six BashHive
hostnames, so `POST /api/sentinel/alert` answers 302 until a dedicated Service Auth application
exists. The scheduled wrapper defaults to Telegram-only and does not read site credentials. See
`docs/ARCHITECTURE.md` and `bash-website/CUTOVER_ACCESS_LOGIN_20260909.md` §T.

`AGENTS.md` holds the binding repository rules and is imported here verbatim:

@AGENTS.md

In practice those rules mean: no code path may accept victim, watchlist, personal-contact,
credential, or private-outbox data; no active scanning or personal monitoring (authoritative
public feeds like CISA KEV are fine); credentials reach the process only as `HIVESEC_*` env vars
at runtime — the scheduled wrapper sources the Telegram bot token and chat id from the git-ignored
repository `.env` (since commit 9c16c12) and reads the `com.hivesec.sentinel.*` Keychain namespace
only for the optional Worker intake; and every live run needs the
`public_brand` profile plus an attribution approval ref (see "Required environment").

## Commands

The repo venv at `.venv` is the canonical interpreter (the LaunchAgent wrapper depends on it).
`docs/ACTIVATION.md` also shows `uv sync --extra dev` / `uv run ...`; either works, but
`AGENTS.md` names `.venv/bin/python -m pytest` as the test gate.

```bash
# one-time setup. The .venv was created by uv (Python 3.13) and has no pip
# (`python -m pip` answers "No module named pip"). Since 18 Sep 2026 it already
# holds the dev extras (pytest, ruff); if they go missing after a rebuild,
# `.venv/bin/python -m pytest` fails. Repopulate it with uv:
uv sync --extra dev            # or: uv run --extra dev pytest -q, to touch nothing
# Only if you rebuild the venv with stdlib venv instead of uv:
#   python3.11 -m venv .venv && .venv/bin/python -m pip install -e '.[dev]'

# test gate (required before reporting completion)
.venv/bin/python -m pytest -q
.venv/bin/python -m pytest tests/test_feeds.py -q                  # one file
.venv/bin/python -m pytest tests/test_feeds.py::test_kev_alerts_include_action_and_source  # one test

# lint (ruff, line-length 100, py311 target)
.venv/bin/ruff check src tests
.venv/bin/ruff format --check src tests   # not enforced by CI, but keep it clean

# CLI dry runs (need the SENTINEL_* env below; no HIVESEC_* credentials needed for --dry-run)
.venv/bin/hivesec-sentinel publish alert.json --dry-run
.venv/bin/hivesec-sentinel refresh-kev --state /tmp/state.json --lookback-days 7 --dry-run
```

`refresh-kev` flags beyond `--state` / `--lookback-days` / `--dry-run`:

- `--record-on {telegram,all}` (default `telegram`) — which channel's acceptance
  marks an alert as seen. The default exists because the site channel is
  blocked: with `all`, a 302 there means nothing is ever recorded and Telegram
  re-sends the same alerts every run.
- `--max-batch N` (default 25, 0 = unlimited) — bounds one run; the rest is left
  for the next and reported as `withheld_for_next_run`.
- `--bootstrap` — first run only: ignore the lookback and publish the whole
  catalogue. Without it a missing state file behaves like any other run.

`refresh-kev` defaults to `--state data/feed_state.json` (`data/` is gitignored) and
`--lookback-days 7` (accepted range 1–30). It exits 1 whenever KEV source health is not `ok`,
even with `--dry-run`, so a failed fetch looks like a failed run.

There is no `requirements.txt`; CI (`.gitlab-ci.yml`, python:3.12 image) installs `.[dev]` and
runs `ruff check src tests` and `pytest -q` as separate jobs. Until 2026-09-13 it installed
without the extras, so pytest was absent, the `|| unittest discover` fallback collected nothing
from this pytest-style suite, and the pipeline was green with zero tests.

## Required environment

`cli.main` calls `profile.resolve_public_brand(os.environ)` right after argparse and before the
publishing subcommands, so every `publish` / `refresh-kev` invocation — including `--dry-run` —
fails unless (`adelaide-report` is exempt: it only reads local state and never publishes):

- `SENTINEL_EXECUTION_PROFILE=public_brand`
- `SENTINEL_POLICY_VERSION=execution-profiles-v1` (default if unset; any other value rejected)
- `SENTINEL_ATTRIBUTION_APPROVAL_REF=<3–160 chars>`
- `SENTINEL_USER_AGENT` optional (defaults to `HiveSec-Sentinel/1.0 (+https://hivesec.eu)`)
- `SENTINEL_SOURCE_REVISION` optional; if set it is copied into each receipt as `source_revision`

Live publishing needs `HIVESEC_TELEGRAM_BOT_TOKEN` and `HIVESEC_TELEGRAM_CHAT_ID`. Site delivery is
disabled by default. An operator may set `HIVESEC_SITE_DELIVERY=enabled` only with the Worker intake:

- **Worker intake, shared secret** (what the live job uses): `HIVESEC_INTAKE_URL` (wrapper
  default `https://hivesec.eu/api/sentinel/alert`) and `HIVESEC_INTAKE_TOKEN`, Keychain item
  `com.hivesec.sentinel.intake-token`, sent as the `X-HiveSec-Token` header and compared by the
  Worker against its `INTAKE_SECRET` as SHA-256 digests. Expected response: HTTP 200.
- **Worker intake, Access service token**: `HIVESEC_CF_CLIENT_ID` / `HIVESEC_CF_CLIENT_SECRET`,
  Keychain items `com.hivesec.sentinel.cf-client-id` / `.cf-client-secret`. **Not configured on
  this machine** (checked 13 Sep 2026) — and it is what an Access Service Auth application would
  need, so this is the channel to restore rather than the shared secret.
GitHub dispatch was removed: it reached GitHub Pages, which no longer serves the sites.

## Architecture

Data flow: `feeds.refresh_kev` → list of alert dicts → `publisher.alert_from_input` (strict
`PublicAlert` contract) → `Publisher.publish` (Telegram, then optional Worker intake) →
`receipts.write_publication_receipts` → `feeds.record_published` (marks IDs as seen).

Module responsibilities:

- `profile.py` — validates the execution-profile env contract into a frozen `PublicBrandContext`.
  This is the gate that makes every run explicit and attributable.
- `publisher.py` — `publish()` returns a single bool and is implemented on
  `publish_detailed()`, which returns the per-channel outcome
  (`{"telegram": bool, "worker": bool}` when enabled); the CLI uses the detailed form so a
  channel that accepted an alert is never re-sent because another failed. `_request` contains
  every transport failure into `False` **and logs it** (channel, host, real status or exception
  type) — do not go back to a bare `except: return False`, that blindness is what let the site
  channel stay dead for days. `PublicAlert` is the versioned public contract (`schema_version` 1, exactly the
  seven fields in `_ALERT_FIELDS`, `source` must equal `"HiveSec Sentinel"`, severity in
  info/warning/critical, message ≤ 6000 chars). `from_dict` rejects **any** extra field, not just
  the `_PRIVATE_FIELDS` list — adding a field to the contract requires bumping `schema_version` and
  updating the BASH site receiver. `sanitize()` strips control chars and redacts token-shaped
  strings before delivery (title capped at 120 chars). `Publisher._request` swallows all network
  errors into `False`.
- `feeds.py` — KEV collection and the delivery-state file (`schema_version: 1`, `seen_ids`,
  `source_health`). `refresh_kev` only *reads* `seen_ids` and writes health; IDs are added to
  `seen_ids` by `record_published`, which the CLI now calls **per alert**, as soon as the channel
  named by `--record-on` (default `telegram`) accepted it. This is the duplicate-suppression
  invariant — an alert already delivered must never be delivered again, and batching that decision
  is what produced a six-hourly repeat on the public bot while the site intake was 302-blocked.
  `refresh_kev(bootstrap=...)` controls a brand-new state file: the function still defaults to
  `True` (ignore the lookback, publish the whole catalog) but the CLI passes `False` unless
  `--bootstrap` is given, so the runbook's "delete the state file" step is no longer a flood.
- `receipts.py` — writes one bounded JSON receipt per **accepted** channel (the CLI passes the
  real channel names; the default is the generic `("telegram", "site")` so a receipt never claims
  a channel that was not used) to
  `~/Library/Application Support/HiveSec Sentinel/publication_receipts/` (0700 dir, 0600 files,
  atomic rename). Receipts deliberately contain the payload SHA-256 and profile metadata but
  **not** the alert title/message; tests assert this.
- `cli.py` — `publish <file>` (single alert; never touches the state file) and `refresh-kev`
  (batch). A batch still stops at the first failure and returns 1, but each alert is recorded and
  receipted as it goes, so work already delivered survives the failure. `--max-batch` (default 25)
  bounds one run. Logging is configured to stderr here, which is what routes the publisher's
  delivery lines into the LaunchAgent error log.

Network is injected for testability: `feeds.fetch_json`/`refresh_kev` take an `opener` callable
(tests pass a lambda returning a fake response object), and `write_publication_receipts` takes a
`receipt_dir`. `Publisher` takes an `opener` (defaults to `urlopen`); `tests/test_publisher.py` injects a fake
and asserts the request shape — never make live calls from tests.

## Operations surface

- `scripts/refresh_public_feed.sh` (zsh) is what launchd runs: exports the SENTINEL_* env with
  `${VAR:-default}` fallbacks, verifies `.venv/bin/hivesec-sentinel` exists (and pip-installs
  `.[dev]` into the venv if it is missing), sources `/Users/raf/Code/sentinel/.env` with
  `set -a` (this is where `HIVESEC_TELEGRAM_BOT_TOKEN` / `HIVESEC_TELEGRAM_CHAT_ID` come from since
  commit 9c16c12; the wrapper exits 1 if either is missing, and any variable set in `.env`
  overrides both the plist and the script defaults), reads Worker intake credentials from Keychain
  only when site delivery was explicitly enabled (shared-secret intake token first, then the
  Access service-token pair), then execs
  `refresh-kev --state "~/Library/Application Support/HiveSec Sentinel/feed_state.json"
  --lookback-days "${SENTINEL_LOOKBACK_DAYS:-7}"`.
- `config/launchd/com.hivesec.sentinel-feed-refresh.plist` — 21600 s interval, `RunAtLoad`; logs to
  `~/Library/Logs/HiveSecSentinel/`. Absolute paths to `/Users/raf/Code/sentinel` are hard-coded
  in both the plist and the script. The repo plist's `EnvironmentVariables` win over the script's
  defaults (attribution ref `PUBLIC-PUBLISH-2026-001`), but the plist **installed** in
  `~/Library/LaunchAgents` (checked 18 Sep 2026) has no `EnvironmentVariables`, so the live job
  uses the script fallback `launchd-kev-refresh` unless `.env` sets it. Reinstalling the plist
  means a reload, and `RunAtLoad` makes that a publishing run.
- `scripts/migrate_keychain_namespace.sh` — historical one-time copy from the legacy Keychain
  services to `com.hivesec.sentinel.*`.
- `docs/OPERATIONS.md` has the restart / inspect / recovery `launchctl` commands. Changing the
  state file layout means updating the recovery procedure there.

Changes to the runbooks, plist, or wrapper script affect a live scheduled job on this machine;
do not reload the LaunchAgent as a side effect of a code change.

## Adelaide report

Adelaide reads only `.adelaide/report.json` (contract v1, /Users/raf/Code/adelaide/docs/REPO_REPORTS.md); this repo keeps ownership of its bot.
`adelaide.py` writes it (atomic, dir 0700, file 0600, ≤ 20 items, ≤ 64 KiB) at the end of every
non-dry-run `refresh-kev` — including a KEV health failure — and on demand with
`hivesec-sentinel adelaide-report --state "<state dir>/feed_state.json"`, which reads only local
state and sends nothing. Items: one `alert` per alert Telegram accepted in the last 48 h (from the
receipts, titled from `adelaide_cache.json` — max 50 entries, 7 days, 0600, next to the state
file; `urgent` when the KEV `dueDate` is under 7 days away, else `high`) plus one `status` item
(`high` if source health is not ok or the last check is older than 12 h, else `low`). The KEV
`dueDate` travels beside the alert through `refresh_kev(due_dates=...)`, never inside
`PublicAlert`. The writer never raises: a failure is one warning log line. Reports older than
48 h are stale for Adelaide, so the 6-hourly job keeps it fresh while the Mac is awake.

## Branch note

`main` is the default branch and what the LaunchAgent runs from the working copy;
`codex/hivesec-feed-hardening` was merged into it on 18 Sep 2026. Keep the working copy on `main`.
