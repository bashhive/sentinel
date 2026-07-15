# HiveSec Sentinel

HiveSec Sentinel is the public security-alert identity for BashHive.

This repository is documentation-only. It must not run a local agent, LaunchAgent, bot
receiver, webhook server or scheduled process.

- Brand: BashHive
- Bot: HiveSec Sentinel
- Telegram: [@hivesecsentinelbot](https://t.me/hivesecsentinelbot)
- Tagline: “AI security assistant for alerts, guidance and security topics.”
- Runtime: `/Users/raf/Code/Butler`
- Public site receiver: `/Users/raf/Code/BASH_site/public_html`

Butler publishes public Cyber Radar MUST alerts through local OMLX, Telegram and GitHub
`repository_dispatch`. The BASH site renders the static public feed through GitHub Pages.

See [PROJECT.md](PROJECT.md), [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) and
[docs/ACTIVATION.md](docs/ACTIVATION.md).
