#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
OTP="${1:-}"

DESTROY_IOT="${DESTROY_IOT:-true}"
DESTROY_HUB="${DESTROY_HUB:-true}"
DESTROY_FOUNDATION="${DESTROY_FOUNDATION:-false}"
export DESTROY_FOUNDATION

cd "${REPO_ROOT}"

if [[ "${DESTROY_IOT}" == "true" ]]; then
  scripts/destroy/destroy-iot-factory-a.sh "${OTP}"
fi

if [[ "${DESTROY_HUB}" == "true" ]]; then
  scripts/destroy/destroy-hub.sh "${OTP}"
fi

if [[ "${DESTROY_FOUNDATION}" == "true" ]]; then
  scripts/destroy/destroy-foundation.sh "${OTP}"
else
  echo "Skipped foundation destroy. Set DESTROY_FOUNDATION=true to include it."
fi

echo "Destroy flow completed."
