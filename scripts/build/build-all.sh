#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
OTP="${1:-}"

# shellcheck disable=SC1091
source "${REPO_ROOT}/scripts/lib/config.sh"
aegis_load_config "${REPO_ROOT}"

BUILD_FOUNDATION="${BUILD_FOUNDATION:-true}"
BUILD_HUB="${BUILD_HUB:-true}"
BUILD_IOT="${BUILD_IOT:-true}"
FACTORY_ID="${FACTORY_ID:-${AEGIS_FACTORY_ID}}"
IOT_CERT_METADATA="${REPO_ROOT}/secret/iot/${FACTORY_ID}/certificate-arn.txt"

cd "${REPO_ROOT}"

if [[ "${BUILD_FOUNDATION}" == "true" || "${BUILD_HUB}" == "true" || \
  ( "${BUILD_IOT}" == "true" && ! -f "${IOT_CERT_METADATA}" ) ]]; then
  # shellcheck disable=SC1091
  source "${REPO_ROOT}/scripts/lib/aws-mfa.sh"
  aegis_ensure_aws_mfa "${OTP}"
fi

if [[ "${BUILD_FOUNDATION}" == "true" ]]; then
  scripts/build/build-foundation.sh "${OTP}"
fi

if [[ "${BUILD_HUB}" == "true" ]]; then
  scripts/build/build-hub.sh "${OTP}"
fi

if [[ "${BUILD_IOT}" == "true" ]]; then
  scripts/build/build-iot-factory-a.sh "${OTP}"
fi

echo "Build flow completed."
