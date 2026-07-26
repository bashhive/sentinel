#!/bin/zsh
# Refresh direct public sources. Secrets remain in macOS Keychain, never in this file or launchd.
set -euo pipefail

repo_dir="/Users/raf/Code/sentinel"
state_dir="$HOME/Library/Application Support/HiveSec Sentinel"
state_path="$state_dir/feed_state.json"
mkdir -p "$state_dir"

export HIVESEC_TELEGRAM_BOT_TOKEN="$(security find-generic-password -s com.hivesec.sentinel.telegram -w)"
export HIVESEC_TELEGRAM_CHAT_ID="$(security find-generic-password -s com.hivesec.sentinel.telegram-chat-id -w)"
export HIVESEC_GITHUB_TOKEN="$(security find-generic-password -s com.hivesec.sentinel.github -w)"
export HIVESEC_GITHUB_REPOSITORY="${HIVESEC_GITHUB_REPOSITORY:-bashhive/bash-website}"

exec "$repo_dir/.venv/bin/hivesec-sentinel" refresh-kev --state "$state_path"
