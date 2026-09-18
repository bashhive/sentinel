# HiveSec Sentinel — project charter

## Goal

Provide the public BashHive cybersecurity-alert identity and the code used by the BASH sites.

## Responsibilities

- Publish general, verified cybersecurity alerts to Telegram and, when explicitly
  enabled, to the authenticated Worker intake.
- Validate the versioned public-alert contract and reject private identities.
- Keep public delivery credentials isolated from private assistants and the scanner.

## Non-responsibilities

- No personal-assistant workflows, calendar, email, LinkedIn or YouTube data.
- No Data Breach Scanner outbox consumer or victim identity.
- No private-assistant, Aspasia, scanner-source or trading credentials.

## Runtime ownership

- Sentinel owns public delivery under `com.hivesec.sentinel.*`, and is the sole
  owner of Telegram delivery.
- The `bash-site` Cloudflare Worker owns static rendering, the gate, the KV
  feed, the authenticated `POST /api/sentinel/alert` intake, **and — since
  10 Sep 2026 — the primary KEV collection**, on a 10-minute Cron Trigger. The
  GitHub `repository_dispatch` path is retired.
- Telegram owns the public `@hivesecsentinelbot` identity.
- Adelaide reads only `.adelaide/report.json` (contract v1, /Users/raf/Code/adelaide/docs/REPO_REPORTS.md); this repo keeps ownership of its bot.
  Sentinel writes that report; Adelaide never publishes through this bot.

Reviewed 13 September 2026. `docs/ARCHITECTURE.md` holds the current data flow
and the reason this repository is no longer what keeps the public feed alive.

## Success criteria

- The repository contains the public publisher and contract tests.
- Public alerts are general cybersecurity facts, never personal scanner events.
- The public site receives only the versioned `PublicAlert` contract.

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) and
[docs/ACTIVATION.md](docs/ACTIVATION.md).
