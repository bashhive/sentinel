# HiveSec Sentinel

HiveSec Sentinel is the public security-alert identity for BashHive.

This repository contains the public publication code and contract for the BASH sites and
`@hivesecsentinelbot`. It handles only verified general cybersecurity alerts.

- Brand: BashHive
- Bot: HiveSec Sentinel
- Telegram: [@hivesecsentinelbot](https://t.me/hivesecsentinelbot)
- Tagline: “AI security assistant for alerts, guidance and security topics.”
- Runtime: this repository, invoked by a macOS LaunchAgent or an explicit operator job
- Public site receiver: the `bash-site` Cloudflare Worker (`/Users/raf/Code/bash-website`),
  endpoint `POST https://hivesec.eu/api/sentinel/alert`

`hivesec-sentinel publish ALERT.json` validates that an alert is public, sends it through
`@hivesecsentinelbot`, and posts it to the site feed.

> **Since 10 September 2026 this repository is not what keeps the public feed current.** The
> Worker collects CISA KEV itself every 10 minutes; this agent is redundant for the site and
> exclusive only for Telegram. Its site channel is currently blocked by Cloudflare Access (302).
> See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) and [CHANGELOG.md](CHANGELOG.md). Credentials come only from
the `HIVESEC_*` environment at runtime and must never be stored in this repository.

See [PROJECT.md](PROJECT.md), [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md),
[docs/ACTIVATION.md](docs/ACTIVATION.md) and [docs/OPERATIONS.md](docs/OPERATIONS.md).

The macOS refresh job is installed from `config/launchd/com.hivesec.sentinel-feed-refresh.plist`;
its wrapper uses the repository virtualenv, validates Keychain prerequisites, stores state and
receipts under Application Support, and suppresses old or previously published alerts.

Delivery is tracked per alert and per channel: an alert is marked as seen as soon as the channel
named by `--record-on` (default `telegram`) accepts it, each attempt is logged with its real
status, `--max-batch` bounds a single run, and the full catalogue is published only with an
explicit `--bootstrap`. See [CHANGELOG.md](CHANGELOG.md) for 2026-09-13.
