#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
OTP="${1:-}"
FACTORY_ID="${FACTORY_ID:-}"

cd "${REPO_ROOT}"

# shellcheck disable=SC1091
source "${REPO_ROOT}/scripts/lib/config.sh"
aegis_load_config "${REPO_ROOT}"
FACTORY_ID="${FACTORY_ID:-${AEGIS_FACTORY_ID}}"

if [[ ! -f "${REPO_ROOT}/secret/iot/${FACTORY_ID}/certificate-arn.txt" ]]; then
  scripts/iot/register-thing.sh "${OTP}"
else
  echo "IoT certificate metadata already exists. Skipping Thing/certificate registration."
fi

scripts/iot/register-k3s-secret.sh
