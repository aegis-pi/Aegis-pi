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

scripts/iot/register-thing.sh "${OTP}"
scripts/iot/register-k3s-secret.sh
