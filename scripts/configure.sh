#!/bin/zsh
set -euo pipefail

ROOT="${0:A:h:h}"

store_secret() {
  local service="$1"
  local account="$2"
  local label="$3"

  echo
  echo "$label"
  /usr/bin/security add-generic-password \
    -U \
    -a "$account" \
    -s "$service" \
    -l "$label" \
    -w
}

echo "HiveSec Sentinel — secure local configuration"
echo "Never paste these secrets into chat, Git, a plist, or a report."

store_secret "com.hivesec.xai" "api-key" "HiveSec Sentinel xAI API key"
store_secret "com.hivesec.github" "token" "HiveSec Sentinel GitHub token for rafpt/bash-site"
store_secret "com.hivesec.telegram" "bot-token" "Token for @hivesecsentinelbot"

token=$(/usr/bin/security find-generic-password \
  -s "com.hivesec.telegram" \
  -a "bot-token" \
  -w)
identity=$(HIVESEC_TOKEN="$token" python3 - <<'PY'
import json
import os
import urllib.request

token = os.environ["HIVESEC_TOKEN"]
request = urllib.request.Request(
    f"https://api.telegram.org/bot{token}/getMe",
    headers={"User-Agent": "HiveSec-Sentinel/1.0"},
)
with urllib.request.urlopen(request, timeout=10) as response:
    print(json.load(response).get("result", {}).get("username", ""))
PY
)
unset token
if [[ "${identity:l}" != "hivesecsentinelbot" ]]; then
  /usr/bin/security delete-generic-password \
    -s "com.hivesec.telegram" \
    -a "bot-token" >/dev/null
  echo "ERROR: token does not belong to @hivesecsentinelbot; it was removed." >&2
  exit 1
fi
echo "Telegram identity verified: @hivesecsentinelbot"

if ! /usr/bin/security find-generic-password \
  -s "com.hivesec.telegram" \
  -a "chat-id" >/dev/null 2>&1; then
  if existing=$(/usr/bin/security find-generic-password \
    -s "com.butler.telegram" \
    -a "chat-id" \
    -w 2>/dev/null); then
    /usr/bin/security add-generic-password \
      -U \
      -a "chat-id" \
      -s "com.hivesec.telegram" \
      -l "HiveSec Sentinel Telegram chat ID" \
      -w "$existing" >/dev/null
    unset existing
    echo "Reused the existing private Telegram chat ID."
  else
    echo
    echo "Send /start to @hivesecsentinelbot."
    store_secret \
      "com.hivesec.telegram" \
      "chat-id" \
      "Numeric Telegram chat ID for HiveSec Sentinel"
  fi
fi

cd "$ROOT"
if [[ -x "$ROOT/.venv/bin/hivesec-sentinel" ]]; then
  "$ROOT/.venv/bin/hivesec-sentinel" health
else
  PYTHONPATH="$ROOT/src" python3 -m hivesec_sentinel health
fi
