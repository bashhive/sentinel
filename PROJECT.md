# HiveSec Sentinel — project charter

## Goal

Provide the public BashHive security-alert identity without running a separate local
agent. Butler is the only runtime that prepares and publishes HiveSec Sentinel alerts.

## Responsibilities

- Define the public identity, Telegram handle and alert contract.
- Document the system boundary between Butler, the Telegram bot and BASH GitHub Pages.
- Keep legacy Aspasia/Bot code decommissioned.

## Non-responsibilities

- No LaunchAgent.
- No Python package or CLI runtime.
- No Telegram webhook or resident receiver.
- No scanner outbox consumer.
- No Butler, Aspasia, scanner-source or trading credentials.

## Runtime ownership

- Butler owns execution and Keychain access under `com.butler.hivesec.*`.
- BASH site owns static rendering and `repository_dispatch` ingestion.
- Telegram owns the public `@hivesecsentinelbot` identity.

## Success criteria

- The repository contains no active runtime code.
- No `com.hivesec.sentinel` LaunchAgent is installed or required.
- Public alerts are generated only from Butler Cyber Radar public-source MUST items.
- The public site receives only the versioned `PublicAlert` contract.

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) and
[docs/ACTIVATION.md](docs/ACTIVATION.md).
