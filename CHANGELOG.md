# Changelog

Notable changes to HiveSec Sentinel. Newest first. Dates are when the change
took effect on the live job or on the receiving site, not the commit date.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
The companion record on the receiving side is
`/Users/raf/Code/bash-website/CHANGELOG.md`; contract changes must appear in
both.

---

## 2026-09-13 — Delivery is recorded per channel, and failures are visible

### Fixed

- **The public bot no longer repeats itself.** `Publisher.publish` required
  *both* channels to succeed, and `record_published` ran only after the whole
  batch had been published. With the site intake answering 302 behind Cloudflare
  Access, every run delivered the same alerts to `@hivesecsentinelbot` and then
  recorded nothing as seen — so the next run sent them again, every six hours.
  Delivery is now tracked per alert and per channel: an alert accepted by the
  channel named in `--record-on` (default `telegram`) is marked seen even if
  another channel rejected it. `--record-on all` restores the old
  all-channels-or-nothing behaviour.
- **Delivery failures are logged.** `Publisher._request` swallowed every
  `HTTPError`, `URLError`, `TimeoutError` and `OSError` into a bare `False`, so a
  302 from Access, a 401 from a revoked token and a DNS failure were
  indistinguishable — which is how the site channel stayed dead for days without
  an alarm. Each attempt now logs channel, host and the real status or exception,
  and the CLI configures logging to stderr so the lines land in
  `~/Library/Logs/HiveSecSentinel/feed-refresh-error.log`. The function still
  contains the failure and returns `False`; nothing raises.
- **Receipts name the channel that actually accepted the alert.** The default
  was the literal tuple `("telegram", "github")`, and the CLI never overrode it,
  so every alert delivered through the Worker intake was filed as a `github`
  publication. Receipts are the audit evidence for public publication; they were
  wrong.
- **Deleting the state file no longer floods Telegram.** A missing state file set
  `since = date.min`, so the documented recovery step in `docs/OPERATIONS.md`
  would publish the entire KEV catalogue (~1 300 entries) one message at a time.
  The CLI now applies the normal lookback unless `--bootstrap` is passed.

### Added

- `Publisher.publish_detailed(alert)` returning `{"telegram": bool,
  "<site channel>": bool}`. `publish()` keeps its signature and returns
  `all(...)`, so existing callers are unaffected.
- `refresh-kev --max-batch N` (default 25) bounds a single run; the remainder is
  left for the next one and reported as `withheld_for_next_run` in the dry-run
  output.
- `refresh-kev --bootstrap` and `--record-on {telegram,all}`.
- `feeds.refresh_kev(..., bootstrap=...)` plus a test that a new state file
  applies the lookback.

### Changed

- CI (`.gitlab-ci.yml`) installs `.[dev]` and runs `ruff check` and `pytest -q`
  as separate failing jobs. It previously installed without the dev extras, so
  `python -m pytest` was missing, the `|| python -m unittest discover` fallback
  collected zero tests from a pytest-style suite, and the pipeline passed green
  with nothing tested. Pip cache moved inside the project directory.

### Verified on 2026-09-13

- Full suite: **15 passed** (run with an external 3.14 interpreter — the repo
  `.venv` is uv-managed and has neither pip nor pytest installed, the same gap
  the CI job had; `uv sync --extra dev` fixes it).
- `refresh-kev --dry-run` against the live catalogue with a scratch state file:
  `health ok`, **14 eligible alerts**, `withheld 0`. Those 14 are what the next
  scheduled run will deliver — and, this time, record.

### Known state

- Unchanged: the site channel still answers 302 and the Worker cron is still the
  primary KEV collector. What changed is that a blocked site channel now costs
  one failed delivery per alert instead of an unbounded repeat on Telegram.

---

## 2026-09-13 — Documentation caught up with a pipeline that had moved

### Changed

- `docs/ARCHITECTURE.md`, `CLAUDE.md`, `PROJECT.md`, `README.md` and
  `docs/OPERATIONS.md` rewritten around two facts that the docs still denied:
  the CISA KEV collector now runs **inside Cloudflare**, and the site channel is
  **blocked by Cloudflare Access**. The old diagram still showed
  `repository_dispatch` into a GitHub Pages feed, a path that has served nothing
  since 10 September.

### Fixed

- `AGENTS.md` had been replaced by a symlink to `CLAUDE.md`, which deleted the
  15 lines of binding repository rules **and** created a self-import cycle —
  `CLAUDE.md` imports `@AGENTS.md`. Restored as a real file. The
  `bash-website` repo has the symlink the other way round, where it is correct;
  the pattern does not transfer here.

### Known state

- The 6-hourly LaunchAgent is redundant for the site and exclusive only for
  Telegram. `POST /api/sentinel/alert` answers 302 for the live Keychain token.
  Either create an Access Service Auth application for that path, or retire the
  agent — a scheduled job that silently delivers nothing is worse than neither.

---

## 2026-09-10 — Collection moved to the Worker; shared-secret intake

### Changed

- The receiving site now collects CISA KEV itself on a 10-minute Cron Trigger
  (`bash-website/src/kev.js`), a port of `feeds.kev_alerts` with identical ids,
  titles and wording so the two producers dedupe. **The public feed no longer
  depends on this machine being awake** — the previous design froze the feed
  whenever the Mac slept, silently.
- The Worker intake authenticates with a shared secret in `X-HiveSec-Token`
  (`HIVESEC_INTAKE_TOKEN`, Keychain `com.hivesec.sentinel.intake-token`),
  replacing the Cloudflare Access service-token pair as the live channel.

---

## 2026-09-09 — The Worker intake channel

### Added

- `Publisher` gained the Worker intake alongside the legacy GitHub dispatch:
  `HIVESEC_INTAKE_URL` plus either the Access service-token pair or the shared
  secret. `from_env` picks the channel; `__init__` raises if neither is
  complete. `opener` is injected so tests never make live calls.
- `scripts/refresh_public_feed.sh` selects the channel by which Keychain items
  exist: intake token → Access pair → GitHub token.

### Deprecated

- GitHub `repository_dispatch`. It reached the feed through GitHub Pages, which
  no longer serves the sites. It remains only as a last-resort fallback in the
  wrapper and should be read as an outage signal, not as redundancy.

---

## 2026-08-22 — Hardened refresh

### Added

- `docs/OPERATIONS.md`: state, receipts, restart, inspect and recovery
  procedures for the LaunchAgent.
- `.gitlab-ci.yml`.

### Changed

- The refresh wrapper validates Keychain prerequisites before publishing, stores
  state and receipts under Application Support, and suppresses old or already
  published alerts.

---

## 2026-07-26 — Profile gate and receipts

### Added

- `profile.resolve_public_brand`: every run, including `--dry-run`, requires the
  explicit `public_brand` execution profile and a recorded attribution approval
  reference.
- Bounded publication receipts, one per channel, containing the payload SHA-256
  and profile metadata but **never** the alert title or message.
