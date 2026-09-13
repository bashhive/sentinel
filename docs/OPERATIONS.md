# Operations

## Purpose

This document is the operational runbook for the macOS LaunchAgent that refreshes
CISA KEV alerts and publishes only eligible, unseen entries.

## Read this first — the job is no longer load-bearing (13 September 2026)

The public site feed is collected inside Cloudflare by a Worker Cron Trigger
every 10 minutes (`bash-website/src/kev.js`, a port of `feeds.kev_alerts`). This
LaunchAgent is **redundant for the site** and exclusive only for Telegram.

Its site channel is also currently blocked: Cloudflare Access fronts every path
of the BashHive hostnames, so `POST /api/sentinel/alert` answers **302**.
Nothing is lost — a batch that fails records nothing as seen and is retried —
but nothing is delivered to the site either.

Check which half is working:

```bash
# the site feed, collected by the Worker — should be minutes old
cd /Users/raf/Code/bash-website
./node_modules/.bin/wrangler kv key get "source:kev" --binding SENTINEL_FEED --remote

# the intake, as this machine sees it: 302 = blocked, 422 = reached the Worker
TOK=$(security find-generic-password -s com.hivesec.sentinel.intake-token -w) \
  curl -s -o /dev/null -w '%{http_code}\n' -X POST \
  -H "X-HiveSec-Token: $TOK" -H 'content-type: application/json' \
  --data '{"not":"an alert"}' https://hivesec.eu/api/sentinel/alert
```

To restore delivery to the site, create a Cloudflare Access **Service Auth**
application for `api/sentinel/alert`, put its AUD in the Worker's `INTAKE_AUD`,
and store the service token in `com.hivesec.sentinel.cf-client-id` /
`.cf-client-secret`. The wrapper picks that channel up on the next run. The
alternative is to accept the cron as the only collector and retire this agent —
decide, rather than leaving a scheduled job that silently delivers nothing.

## State and receipts

- State: `~/Library/Application Support/HiveSec Sentinel/feed_state.json`
- Receipts: `~/Library/Application Support/HiveSec Sentinel/publication_receipts/`
- Standard output: `~/Library/Logs/HiveSecSentinel/feed-refresh.log`
- Errors: `~/Library/Logs/HiveSecSentinel/feed-refresh-error.log`

The state file records `seen_ids` per alert, as soon as the channel named by
`--record-on` (default `telegram`) accepts it. Alerts older than the configured
lookback or already present in `seen_ids` are suppressed. Until 2026-09-13 the
whole batch had to succeed on **both** channels before anything was recorded,
which — with the site intake blocked — re-sent the same alerts to Telegram every
six hours.

Every delivery attempt now logs one line per channel with the real outcome:

```bash
grep 'delivery ' ~/Library/Logs/HiveSecSentinel/feed-refresh-error.log | tail -20
# delivery accepted: channel=telegram host=api.telegram.org status=200
# delivery failed:   channel=worker host=hivesec.eu status=302 reason=http_error
```

A 302 there is the Access block; a 401 is a bad or revoked token; a
`reason=URLError` line is the network. They used to be indistinguishable.

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

A missing state file no longer publishes the whole KEV catalogue: the CLI applies
the normal lookback unless `--bootstrap` is passed, and `--max-batch` (default 25)
bounds any single run. If you really do want the full catalogue, run it by hand
once, with your eyes on it:

```bash
.venv/bin/hivesec-sentinel refresh-kev \
  --state "$HOME/Library/Application Support/HiveSec Sentinel/feed_state.json" \
  --bootstrap --dry-run | head -40
```

```bash
launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/com.hivesec.sentinel-feed-refresh.plist 2>/dev/null || true
rm -f "$HOME/Library/Application Support/HiveSec Sentinel/feed_state.json"
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.hivesec.sentinel-feed-refresh.plist
launchctl kickstart -k gui/$(id -u)/com.hivesec.sentinel-feed-refresh
```

## Security

Secrets are read from macOS Keychain and are never written to the repository. The
wrapper fails before publication if any required Keychain item is missing.
