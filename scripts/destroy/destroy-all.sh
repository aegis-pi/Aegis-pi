#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
OTP="${1:-}"

# shellcheck disable=SC1091
source "${REPO_ROOT}/scripts/lib/config.sh"
aegis_load_config "${REPO_ROOT}"

DESTROY_IOT="${DESTROY_IOT:-true}"
DESTROY_HUB="${DESTROY_HUB:-true}"
DESTROY_FOUNDATION="${DESTROY_FOUNDATION:-true}"
FOUNDATION_STATE="${REPO_ROOT}/infra/foundation/terraform.tfstate"
export DESTROY_FOUNDATION

cd "${REPO_ROOT}"

if [[ "${DESTROY_IOT}" == "true" || "${DESTROY_HUB}" == "true" || "${DESTROY_FOUNDATION}" == "true" ]]; then
  # shellcheck disable=SC1091
  source "${REPO_ROOT}/scripts/lib/aws-mfa.sh"
  aegis_ensure_aws_mfa "${OTP}"
fi

echo "Destroy scope: iot=${DESTROY_IOT}, hub=${DESTROY_HUB}, foundation=${DESTROY_FOUNDATION}"

if [[ "${DESTROY_IOT}" == "true" ]]; then
  scripts/destroy/destroy-iot-factory-a.sh "${OTP}"
fi

if [[ "${DESTROY_HUB}" == "true" ]]; then
  if [[ ! -f "${FOUNDATION_STATE}" ]]; then
    echo "Hub destroy requires ${FOUNDATION_STATE} because infra/hub reads foundation outputs for AMP/IRSA wiring." >&2
    echo "Restore the foundation state file, or set DESTROY_HUB=false if hub resources are already gone." >&2
    exit 1
  fi

  scripts/destroy/destroy-hub.sh "${OTP}"
fi

if [[ "${DESTROY_FOUNDATION}" == "true" ]]; then
  scripts/destroy/destroy-foundation.sh "${OTP}"
else
  echo "Skipped foundation destroy. Set DESTROY_FOUNDATION=true to include it."
fi

echo "Destroy flow completed."
