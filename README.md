# HiveSec Sentinel

Independent security-alert publishing pipeline for BashHive.

- Telegram: [@hivesecsentinelbot](https://t.me/hivesecsentinelbot)
- Public panel: `bash.pt` through `rafpt/bash-site`
- Intelligence input: the latest local Butler Cyber Radar
- Executive enrichment: xAI Grok, invoked once per new report
- Runtime: a macOS LaunchAgent at 07:45 with `KeepAlive=false`

HiveSec Sentinel owns all Grok, public-site and HiveSec Telegram responsibilities. Butler only
produces its local report and operates `@butleradelaidebot`; it has no HiveSec credentials or
publishing code.

## Quick start

```bash
cd "/Users/raf/Code/HiveSec Sentinel"
uv sync --extra dev
uv run hivesec-sentinel health
uv run hivesec-sentinel publish --dry-run
./scripts/configure.sh
./scripts/install_launch_agent.sh
```

Runtime state is stored under `~/Library/Application Support/HiveSec Sentinel`. Credentials are
read from dedicated macOS Keychain services:

- `com.hivesec.xai` / `api-key`
- `com.hivesec.telegram` / `bot-token` and `chat-id`
- `com.hivesec.github` / `token`

No credential is stored in this repository, the Butler project, reports, logs, or launchd
plists.

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) and
[docs/ACTIVATION.md](docs/ACTIVATION.md).
