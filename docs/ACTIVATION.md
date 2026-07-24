# Activation

HiveSec Sentinel is activated from this repository, independently from Butler.

## Configure

```bash
cd "/Users/raf/Code/sentinel"
uv sync --extra dev
```

The approved secret store supplies dedicated credentials for:

- `HIVESEC_TELEGRAM_BOT_TOKEN`
- `HIVESEC_TELEGRAM_CHAT_ID`
- `HIVESEC_GITHUB_TOKEN`

## Validate

```bash
cd "/Users/raf/Code/sentinel"
uv run pytest
uv run hivesec-sentinel publish alert.json --dry-run
```

## Do not install

Do not configure Butler or Data Breach Scanner credentials here. Deploy only after the public
site has supplied `HIVESEC_TELEGRAM_BOT_TOKEN`, `HIVESEC_TELEGRAM_CHAT_ID` and
`HIVESEC_GITHUB_TOKEN` through its approved secret store.

## Periodic source validation

`scripts/refresh_public_feed.sh` checks the official CISA Known Exploited Vulnerabilities
catalog every six hours. It keeps its delivery state under `~/Library/Application Support/HiveSec Sentinel/`
and retrieves credentials from Keychain at runtime; no secret is stored in the script or plist.

The refresh script reuses the existing legacy Keychain entries for the Telegram bot token and
GitHub token. Install `config/launchd/com.hivesec.sentinel-feed-refresh.plist` only after the
`HIVESEC_TELEGRAM_CHAT_ID` Keychain entry has been confirmed. The job publishes a new alert only
after both Telegram and the public-site dispatch succeed, then records it as delivered to prevent
duplicates.
