#!/bin/zsh
set -euo pipefail

DESTINATION="$HOME/Library/LaunchAgents/com.hivesec.sentinel.plist"
DOMAIN="gui/$UID"

launchctl bootout "$DOMAIN" "$DESTINATION" 2>/dev/null || true
rm -f "$DESTINATION"
echo "Removed com.hivesec.sentinel"
