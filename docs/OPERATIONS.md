# Operations

## Purpose

This document is the operational runbook for the macOS LaunchAgent that refreshes
CISA KEV alerts and publishes only eligible, unseen entries.

## State and receipts

- State: `~/Library/Application Support/HiveSec Sentinel/feed_state.json`
- Receipts: `~/Library/Application Support/HiveSec Sentinel/publication_receipts/`
- Standard output: `~/Library/Logs/HiveSecSentinel/feed-refresh.log`
- Errors: `~/Library/Logs/HiveSecSentinel/feed-refresh-error.log`

The state file records `seen_ids` only after successful publication. Alerts older
than the configured lookback or already present in `seen_ids` are suppressed.

## Validate

```bash
cd /Users/raf/Code/sentinel
source .venv/bin/activate
python -m pip install -e ".[dev]"
python -m pytest -q
ruff check src tests
```

## Restart

```bash
launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/com.hivesec.sentinel-feed-refresh.plist 2>/dev/null || true
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.hivesec.sentinel-feed-refresh.plist
launchctl kickstart -k gui/$(id -u)/com.hivesec.sentinel-feed-refresh
```

## Inspect

```bash
launchctl print gui/$(id -u)/com.hivesec.sentinel-feed-refresh
tail -n 120 ~/Library/Logs/HiveSecSentinel/feed-refresh-error.log
tail -n 120 ~/Library/Logs/HiveSecSentinel/feed-refresh.log
```

## Recovery

If a bad state must be discarded, stop the agent, remove only the state file, then
restart it. This intentionally re-evaluates the feed and should be followed by a
manual review of the first publication batch.

```bash
launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/com.hivesec.sentinel-feed-refresh.plist 2>/dev/null || true
rm -f "$HOME/Library/Application Support/HiveSec Sentinel/feed_state.json"
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.hivesec.sentinel-feed-refresh.plist
launchctl kickstart -k gui/$(id -u)/com.hivesec.sentinel-feed-refresh
```

## Security

Secrets are read from macOS Keychain and are never written to the repository. The
wrapper fails before publication if any required Keychain item is missing.
