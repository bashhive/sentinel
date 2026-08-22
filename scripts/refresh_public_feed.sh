#!/bin/zsh
# Refresh direct public sources through the repository-managed virtualenv.
set -euo pipefail

repo_dir="/Users/raf/Code/sentinel"
state_dir="$HOME/Library/Application Support/HiveSec Sentinel"
state_path="$state_dir/feed_state.json"
log_dir="$HOME/Library/Logs/HiveSecSentinel"
mkdir -p "$state_dir" "$log_dir"
cd "$repo_dir"
export PATH="$repo_dir/.venv/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
export SENTINEL_EXECUTION_PROFILE="${SENTINEL_EXECUTION_PROFILE:-public_brand}"
export SENTINEL_POLICY_VERSION="${SENTINEL_POLICY_VERSION:-execution-profiles-v1}"
export SENTINEL_ATTRIBUTION_APPROVAL_REF="${SENTINEL_ATTRIBUTION_APPROVAL_REF:-launchd-kev-refresh}"
export SENTINEL_USER_AGENT="${SENTINEL_USER_AGENT:-HiveSec-Sentinel/1.0 (+https://hivesec.eu)}"
export HIVESEC_GITHUB_REPOSITORY="${HIVESEC_GITHUB_REPOSITORY:-bashhive/bash-website}"

python_bin="$repo_dir/.venv/bin/python"
if [[ ! -x "$python_bin" ]]; then
  echo "missing Python virtualenv: $python_bin" >&2
  exit 1
fi
if [[ ! -x "$repo_dir/.venv/bin/hivesec-sentinel" ]]; then
  echo "missing executable: $repo_dir/.venv/bin/hivesec-sentinel" >&2
  "$python_bin" -m ensurepip --upgrade >/dev/null 2>&1 || true
  "$python_bin" -m pip install -e "$repo_dir[dev]" >/dev/null
fi

for service in com.hivesec.sentinel.telegram com.hivesec.sentinel.telegram-chat-id com.hivesec.sentinel.github; do
  if ! security find-generic-password -s "$service" -w >/dev/null 2>&1; then
    echo "missing Keychain item: $service" >&2
    exit 1
  fi
done
export HIVESEC_TELEGRAM_BOT_TOKEN="$(security find-generic-password -s com.hivesec.sentinel.telegram -w)"
export HIVESEC_TELEGRAM_CHAT_ID="$(security find-generic-password -s com.hivesec.sentinel.telegram-chat-id -w)"
export HIVESEC_GITHUB_TOKEN="$(security find-generic-password -s com.hivesec.sentinel.github -w)"

exec "$repo_dir/.venv/bin/hivesec-sentinel" refresh-kev --state "$state_path" --lookback-days "${SENTINEL_LOOKBACK_DAYS:-7}"
