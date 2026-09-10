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

for service in com.hivesec.sentinel.telegram com.hivesec.sentinel.telegram-chat-id; do
  if ! security find-generic-password -s "$service" -w >/dev/null 2>&1; then
    echo "missing Keychain item: $service" >&2
    exit 1
  fi
done
export HIVESEC_TELEGRAM_BOT_TOKEN="$(security find-generic-password -s com.hivesec.sentinel.telegram -w)"
export HIVESEC_TELEGRAM_CHAT_ID="$(security find-generic-password -s com.hivesec.sentinel.telegram-chat-id -w)"

# Site channel. Preferred: the bash-site Worker intake, authenticated with a
# Cloudflare Access service token stored in Keychain as
#   com.hivesec.sentinel.cf-client-id / com.hivesec.sentinel.cf-client-secret
# Legacy: GitHub repository_dispatch with com.hivesec.sentinel.github.
# The Worker intake is used whenever both Keychain items exist; otherwise the
# GitHub token is required. See bash-website/CUTOVER_ACCESS_LOGIN_20260909.md.
export HIVESEC_INTAKE_URL="${HIVESEC_INTAKE_URL:-https://hivesec.eu/api/sentinel/alert}"
if security find-generic-password -s com.hivesec.sentinel.intake-token -w >/dev/null 2>&1; then
  # Preferred: shared secret, matched against the Worker's INTAKE_SECRET.
  export HIVESEC_INTAKE_TOKEN="$(security find-generic-password -s com.hivesec.sentinel.intake-token -w)"
elif security find-generic-password -s com.hivesec.sentinel.cf-client-id -w >/dev/null 2>&1 \
   && security find-generic-password -s com.hivesec.sentinel.cf-client-secret -w >/dev/null 2>&1; then
  # Legacy: Cloudflare Access service token (only works while an Access intake app exists).
  export HIVESEC_CF_CLIENT_ID="$(security find-generic-password -s com.hivesec.sentinel.cf-client-id -w)"
  export HIVESEC_CF_CLIENT_SECRET="$(security find-generic-password -s com.hivesec.sentinel.cf-client-secret -w)"
else
  # Last resort: GitHub repository_dispatch. Loses alerts in bursts — see the
  # bash-website audit — so keep the intake token present.
  unset HIVESEC_INTAKE_URL
  if ! security find-generic-password -s com.hivesec.sentinel.github -w >/dev/null 2>&1; then
    echo "missing Keychain item: com.hivesec.sentinel.intake-token (or the cf pair, or .github)" >&2
    exit 1
  fi
  export HIVESEC_GITHUB_TOKEN="$(security find-generic-password -s com.hivesec.sentinel.github -w)"
fi

exec "$repo_dir/.venv/bin/hivesec-sentinel" refresh-kev --state "$state_path" --lookback-days "${SENTINEL_LOOKBACK_DAYS:-7}"
