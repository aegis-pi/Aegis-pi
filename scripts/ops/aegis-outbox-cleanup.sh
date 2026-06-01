#!/usr/bin/env bash
set -euo pipefail

OUTBOX_DIR="${AEGIS_OUTBOX_DIR:-/var/lib/aegis/outbox}"
MIN_AGE_MINUTES="${AEGIS_OUTBOX_CLEANUP_MIN_AGE_MINUTES:-1440}"
LOG_FILE="${AEGIS_OUTBOX_CLEANUP_LOG_FILE:-/var/log/aegis-outbox-cleanup.log}"

timestamp() {
  date -u +"%Y-%m-%dT%H:%M:%SZ"
}

if [[ ! -d "${OUTBOX_DIR}" ]]; then
  echo "$(timestamp) skip missing outbox: ${OUTBOX_DIR}" >>"${LOG_FILE}"
  exit 0
fi

deleted_count="$(
  find "${OUTBOX_DIR}" \
    -maxdepth 1 \
    -type f \
    -name '*.json' \
    -mmin +"${MIN_AGE_MINUTES}" \
    -print \
    -delete | wc -l
)"

echo "$(timestamp) deleted=${deleted_count} outbox=${OUTBOX_DIR} min_age_minutes=${MIN_AGE_MINUTES}" >>"${LOG_FILE}"
