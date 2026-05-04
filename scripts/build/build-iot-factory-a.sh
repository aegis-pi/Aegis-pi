#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
OTP="${1:-}"

cd "${REPO_ROOT}"

if [[ ! -f "${REPO_ROOT}/secret/iot/factory-a/certificate-arn.txt" ]]; then
  scripts/iot/register-thing.sh "${OTP}"
else
  echo "IoT certificate metadata already exists. Skipping Thing/certificate registration."
fi

scripts/iot/register-k3s-secret.sh
