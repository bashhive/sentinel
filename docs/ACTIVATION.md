# Activation

## 1. Configure isolated credentials

Add [`@hivesecsentinelbot`](https://t.me/hivesecsentinelbot) to the intended public
channel/group, then run:

```bash
cd "/Users/raf/Code/HiveSec Sentinel"
./scripts/configure.sh
```

The setup verifies the Telegram bot identity. Use a GitHub token limited to the BASH site
repository and only the permissions required for `repository_dispatch`.

## 2. Validate

```bash
uv run hivesec-sentinel health
uv run hivesec-sentinel consume --dry-run
make check
plutil -lint config/launchd/com.hivesec.sentinel.plist
```

Dry-run performs no network delivery and does not move an event.

## 3. Install

```bash
./scripts/install_launch_agent.sh
launchctl print gui/$UID/com.hivesec.sentinel
```

The consumer checks the scanner's public outbox every five minutes. Never point
`HIVESEC_SCANNER_OUTBOX_ROOT` at its `private` directory.
