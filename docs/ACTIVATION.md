# Activation

HiveSec Sentinel is activated from Butler, not from this repository.

## Configure

```bash
cd "/Users/raf/Code/Butler"
./scripts/configure_hivesec_sentinel.sh
```

The script stores dedicated credentials in:

- `com.butler.hivesec.telegram`
- `com.butler.hivesec.github`

## Validate

```bash
cd "/Users/raf/Code/Butler"
uv run butler health
uv run butler radar run --dry-run
make check
```

## Do not install

Do not install or restore `com.hivesec.sentinel`. HiveSec Sentinel has no local
LaunchAgent and no resident receiver.
