#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

OTP="${1:-}"

cd "${REPO_ROOT}"
# shellcheck disable=SC1091
source "${REPO_ROOT}/scripts/lib/aws-mfa.sh"
aegis_ensure_aws_mfa "${OTP}"

scripts/build/build-hub.sh "${OTP}"
exec scripts/ops/argocd-port-forward.sh
