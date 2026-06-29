# HiveSec Sentinel

Public security-alert publisher for the BASH sites.

- Telegram: [@hivesecsentinelbot](https://t.me/hivesecsentinelbot)
- Public panel: `bash.pt` through `rafpt/bash-site`
- Input: public-only events from the local Data Breach Scanner outbox
- Enrichment: xAI Grok, invoked only after the scanner classifies an event as public
- Runtime: macOS LaunchAgent polling every five minutes

HiveSec owns Grok, public-site and public Telegram credentials. It cannot read the scanner's
private outbox and has no Butler or Aspasia credentials.

## Quick start

```bash
cd "/Users/raf/Code/HiveSec Sentinel"
uv sync --extra dev
uv run hivesec-sentinel health
uv run hivesec-sentinel consume --dry-run
./scripts/configure.sh
./scripts/install_launch_agent.sh
```

Credentials remain in the dedicated `com.hivesec.*` macOS Keychain services. No token is
stored in this repository, event files, logs or launchd plists.

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) and
[docs/ACTIVATION.md](docs/ACTIVATION.md).
