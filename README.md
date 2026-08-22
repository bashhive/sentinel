# HiveSec Sentinel

HiveSec Sentinel is the public security-alert identity for BashHive.

This repository contains the public publication code and contract for the BASH sites and
`@hivesecsentinelbot`. It handles only verified general cybersecurity alerts.

- Brand: BashHive
- Bot: HiveSec Sentinel
- Telegram: [@hivesecsentinelbot](https://t.me/hivesecsentinelbot)
- Tagline: “AI security assistant for alerts, guidance and security topics.”
- Runtime: this repository, invoked by the public-site deployment or an explicit operator job
- Public site receiver: `/Users/raf/Code/BASH_site/public_html`

`hivesec-sentinel publish ALERT.json` validates that an alert is public, sends it through
`@hivesecsentinelbot`, and dispatches it to the BASH site feed. Credentials come only from
the `HIVESEC_*` environment at runtime and must never be stored in this repository.

See [PROJECT.md](PROJECT.md), [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md),
[docs/ACTIVATION.md](docs/ACTIVATION.md) and [docs/OPERATIONS.md](docs/OPERATIONS.md).

The macOS refresh job is installed from `config/launchd/com.hivesec.sentinel-feed-refresh.plist`;
its wrapper uses the repository virtualenv, validates Keychain prerequisites, stores state and
receipts under Application Support, and suppresses old or previously published alerts.
