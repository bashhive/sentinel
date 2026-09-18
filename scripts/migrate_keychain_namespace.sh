#!/bin/bash
set -euo pipefail

migrate_secret() {
  local old_service="$1"
  local new_service="$2"
  local account="$3"
  local value
  if security find-generic-password -s "${new_service}" >/dev/null 2>&1; then
    printf 'Already present: %s\n' "${new_service}"
    return
  fi
  value="$(security find-generic-password -s "${old_service}" -w)"
  security add-generic-password \
    -U -a "${account}" -s "${new_service}" -w "${value}" >/dev/null
  unset value
  printf 'Migrated Keychain service: %s\n' "${new_service}"
}

migrate_secret \
  "com.butler.hivesec.telegram" \
  "com.hivesec.sentinel.telegram" \
  "hivesec-sentinel"
migrate_secret \
  "HIVESEC_TELEGRAM_CHAT_ID" \
  "com.hivesec.sentinel.telegram-chat-id" \
  "hivesec-sentinel"
printf 'Sentinel Keychain namespace migration completed without printing secret values.\n'
