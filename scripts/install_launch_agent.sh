#!/bin/zsh
set -euo pipefail

ROOT="${0:A:h:h}"
TEMPLATE="$ROOT/config/launchd/com.hivesec.sentinel.plist"
DESTINATION="$HOME/Library/LaunchAgents/com.hivesec.sentinel.plist"
DATA_DIR="${HIVESEC_DATA_DIR:-$HOME/Library/Application Support/HiveSec Sentinel}"
SCANNER_OUTBOX="${HIVESEC_SCANNER_OUTBOX_ROOT:-$HOME/Library/Application Support/Data Breach Scanner/outbox}"
LOGS_DIR="$HOME/Library/Logs/HiveSec Sentinel"
DOMAIN="gui/$UID"

if [[ -n "${HIVESEC_PYTHON:-}" ]]; then
  PYTHON_BIN="$HIVESEC_PYTHON"
elif [[ -x "$ROOT/.venv/bin/python" ]]; then
  PYTHON_BIN="$ROOT/.venv/bin/python"
else
  PYTHON_BIN="$(command -v python3)"
fi

mkdir -p "${DESTINATION:h}" "$DATA_DIR" "$LOGS_DIR"
sed \
  -e "s|__PYTHON__|$PYTHON_BIN|g" \
  -e "s|__ROOT__|$ROOT|g" \
  -e "s|__DATA__|$DATA_DIR|g" \
  -e "s|__SCANNER_OUTBOX__|$SCANNER_OUTBOX|g" \
  -e "s|__LOGS__|$LOGS_DIR|g" \
  "$TEMPLATE" > "$DESTINATION"

plutil -lint "$DESTINATION"
launchctl bootout "$DOMAIN" "$DESTINATION" 2>/dev/null || true
launchctl bootstrap "$DOMAIN" "$DESTINATION"
launchctl enable "$DOMAIN/com.hivesec.sentinel"
launchctl print "$DOMAIN/com.hivesec.sentinel" >/dev/null

echo "Installed com.hivesec.sentinel (public outbox poll every 5 minutes)"
