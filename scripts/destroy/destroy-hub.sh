#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
OTP="${1:-}"

# shellcheck disable=SC1091
source "${REPO_ROOT}/scripts/lib/config.sh"
aegis_load_config "${REPO_ROOT}"
# shellcheck disable=SC1091
source "${REPO_ROOT}/scripts/lib/aws-mfa.sh"
# shellcheck disable=SC1091
source "${REPO_ROOT}/scripts/lib/terraform.sh"
aegis_ensure_aws_mfa "${OTP}"

aegis_terraform_destroy_root "${REPO_ROOT}/infra/hub"
