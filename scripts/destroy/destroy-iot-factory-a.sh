#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
OTP="${1:-}"

cd "${REPO_ROOT}"

if [[ "${SKIP_K3S_IOT_SECRET_DESTROY:-false}" != "true" ]]; then
  scripts/destroy/destroy-k3s-iot-secret.sh
fi
scripts/iot/cleanup-thing.sh "${OTP}"
