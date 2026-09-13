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
# The Worker cron is now the authoritative site collector.  Keep the local
# LaunchAgent Telegram-only until a narrowly scoped Access intake exists.
export HIVESEC_SITE_DELIVERY="${HIVESEC_SITE_DELIVERY:-disabled}"

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

for service in com.hivesec.sentinel.telegram com.hivesec.sentinel.telegram-chat-id; do
  if ! security find-generic-password -s "$service" -w >/dev/null 2>&1; then
    echo "missing Keychain item: $service" >&2
    exit 1
  fi
done
export HIVESEC_TELEGRAM_BOT_TOKEN="$(security find-generic-password -s com.hivesec.sentinel.telegram -w)"
export HIVESEC_TELEGRAM_CHAT_ID="$(security find-generic-password -s com.hivesec.sentinel.telegram-chat-id -w)"

# Site channel, only when explicitly enabled. Preferred: the bash-site Worker intake, authenticated with a
# Cloudflare Access service token stored in Keychain as
#   com.hivesec.sentinel.cf-client-id / com.hivesec.sentinel.cf-client-secret
# GitHub repository_dispatch was retired with GitHub Pages and is not a fallback.
if [[ "$HIVESEC_SITE_DELIVERY" == "enabled" ]]; then
  export HIVESEC_INTAKE_URL="${HIVESEC_INTAKE_URL:-https://hivesec.eu/api/sentinel/alert}"
  if security find-generic-password -s com.hivesec.sentinel.intake-token -w >/dev/null 2>&1; then
    # Preferred: shared secret, matched against the Worker's INTAKE_SECRET.
    export HIVESEC_INTAKE_TOKEN="$(security find-generic-password -s com.hivesec.sentinel.intake-token -w)"
  elif security find-generic-password -s com.hivesec.sentinel.cf-client-id -w >/dev/null 2>&1 \
   && security find-generic-password -s com.hivesec.sentinel.cf-client-secret -w >/dev/null 2>&1; then
    # Service Auth, only after an Access intake application exists.
    export HIVESEC_CF_CLIENT_ID="$(security find-generic-password -s com.hivesec.sentinel.cf-client-id -w)"
    export HIVESEC_CF_CLIENT_SECRET="$(security find-generic-password -s com.hivesec.sentinel.cf-client-secret -w)"
  else
    unset HIVESEC_INTAKE_URL
    echo "site delivery enabled but no Worker intake credentials are configured" >&2
    exit 1
  fi
elif [[ "$HIVESEC_SITE_DELIVERY" != "disabled" ]]; then
  echo "invalid HIVESEC_SITE_DELIVERY: $HIVESEC_SITE_DELIVERY" >&2
  exit 1
fi

exec "$repo_dir/.venv/bin/hivesec-sentinel" refresh-kev --state "$state_path" --lookback-days "${SENTINEL_LOOKBACK_DAYS:-7}"
