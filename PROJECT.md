# HiveSec Sentinel — project charter

## Goal

Provide the public BashHive cybersecurity-alert identity and the code used by the BASH sites.

## Responsibilities

- Publish general, verified cybersecurity alerts to the BASH sites and Telegram handle.
- Validate the versioned public-alert contract and reject private identities.
- Keep public delivery credentials isolated from Butler and the scanner.

## Non-responsibilities

- No personal-assistant workflows, calendar, email, LinkedIn or YouTube data.
- No Data Breach Scanner outbox consumer or victim identity.
- No Butler, Aspasia, scanner-source or trading credentials.

## Runtime ownership

- Sentinel owns public delivery under `com.hivesec.sentinel.*`.
- BASH site owns static rendering and `repository_dispatch` ingestion.
- Telegram owns the public `@hivesecsentinelbot` identity.

## Success criteria

- The repository contains the public publisher and contract tests.
- Public alerts are general cybersecurity facts, never personal scanner events.
- The public site receives only the versioned `PublicAlert` contract.

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) and
[docs/ACTIVATION.md](docs/ACTIVATION.md).
