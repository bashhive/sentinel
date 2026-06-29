# HiveSec Sentinel — project charter

## Goal

Publish high-confidence, globally relevant leak and dark-web exposure
intelligence to public BASH channels without receiving personal victim data.

## Responsibilities

- Consume only the Data Breach Scanner public outbox.
- Convert a validated public event into a bounded PT-PT executive alert.
- Use Grok for editorial synthesis with deterministic fallback.
- Deliver the same public contract to `@hivesecsentinelbot` and the BASH site
  through GitHub `repository_dispatch`.
- Preserve retry state until both channels confirm delivery.

## Boundaries

- Telegram identity: `@hivesecsentinelbot`.
- The project cannot read the scanner private outbox.
- Any event containing `victim` is rejected before Grok or delivery.
- It has no Butler, Aspasia or scanner-source credentials.
- Grok sees only already-public, bounded event JSON marked as untrusted input.

## Implemented changes — 2026-06-29

- Extracted HiveSec/Grok/public publishing from Butler into this standalone
  project.
- Replaced Butler Markdown report ingestion with the scanner public-event
  contract.
- Added schema, ID, file type, path, size and private-field validation.
- Added secret-pattern redaction and deterministic degraded summaries.
- Added Telegram and GitHub delivery clients with dedicated Keychain namespaces.
- Added per-channel durable retry progress and move-after-dual-success semantics.
- Replaced the 07:45 report schedule with a five-minute public-outbox poll.
- Added unit tests, activation documentation and BASH receiver validation.

## Operations

```bash
make check
uv run hivesec-sentinel health
uv run hivesec-sentinel consume --dry-run
./scripts/configure.sh
./scripts/install_launch_agent.sh
launchctl print gui/$UID/com.hivesec.sentinel
```

Do not install the LaunchAgent until the dedicated Telegram, xAI and GitHub
credentials pass `health`.

## Success criteria

- No personal identity can cross the public boundary.
- Telegram and site receive identical versioned alerts.
- A temporary Grok failure still permits deterministic publication.
- A channel failure leaves the event pending and does not repeat a channel that
  already succeeded.
- The process exposes no inbound listener or remote Butler interface.

## Next goals

1. Configure and verify the three dedicated credentials.
2. Publish the current public outbox and confirm site rendering.
3. Add source-quality and publication-latency dashboards after stable operation.

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) and
[docs/ACTIVATION.md](docs/ACTIVATION.md).
