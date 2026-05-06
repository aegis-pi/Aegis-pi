#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
OTP="${1:-}"

if [[ "${DESTROY_FOUNDATION:-false}" != "true" ]]; then
  echo "Refusing to destroy foundation resources by default." >&2
  echo "Set DESTROY_FOUNDATION=true to destroy S3/AMP/IoT Rule durable resources." >&2
  exit 1
fi

# shellcheck disable=SC1091
source "${REPO_ROOT}/scripts/lib/config.sh"
aegis_load_config "${REPO_ROOT}"
# shellcheck disable=SC1091
source "${REPO_ROOT}/scripts/lib/aws-mfa.sh"
# shellcheck disable=SC1091
source "${REPO_ROOT}/scripts/lib/terraform.sh"
aegis_ensure_aws_mfa "${OTP}"

aegis_terraform_destroy_root "${REPO_ROOT}/infra/foundation"
