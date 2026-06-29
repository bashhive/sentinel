# Activation

## 1. Configure dedicated credentials

Send `/start` to
[`@hivesecsentinelbot`](https://t.me/hivesecsentinelbot), then run:

```bash
cd "/Users/raf/Code/HiveSec Sentinel"
./scripts/configure.sh
```

The setup verifies that the BotFather token belongs to `@hivesecsentinelbot`. The existing
private Telegram chat ID may be reused, but tokens are never copied from Butler.

The GitHub fine-grained token must be limited to `rafpt/bash-site` and allow repository
dispatch/contents updates required by its workflow.

## 2. Validate locally

```bash
uv run hivesec-sentinel health
uv run hivesec-sentinel publish --dry-run
uv run hivesec-sentinel delivery-test
```

The dry run performs no network delivery and writes no state.

## 3. Install the schedule

```bash
./scripts/install_launch_agent.sh
launchctl print gui/$UID/com.hivesec.sentinel
```

HiveSec runs at 07:45, after Butler's 07:30 radar. Reprocessing the same report is skipped unless
`--force` is used.

## 4. Activate BASH Pages

Commit and push the reviewed `/Users/raf/Code/BASH_site/public_html` changes. Configure
`rafpt/bash-site` GitHub Pages to use GitHub Actions while preserving the existing `bash.pt`
custom domain and HTTPS enforcement.
