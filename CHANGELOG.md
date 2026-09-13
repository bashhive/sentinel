# Changelog

Notable changes to HiveSec Sentinel. Newest first. Dates are when the change
took effect on the live job or on the receiving site, not the commit date.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
The companion record on the receiving side is
`/Users/raf/Code/bash-website/CHANGELOG.md`; contract changes must appear in
both.

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
