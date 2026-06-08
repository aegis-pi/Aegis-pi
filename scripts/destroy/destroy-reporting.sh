#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
OTP="${1:-}"
REPORTING_ROOT="${REPO_ROOT}/infra/reporting"

# shellcheck disable=SC1091
source "${REPO_ROOT}/scripts/lib/config.sh"
aegis_load_config "${REPO_ROOT}"
# shellcheck disable=SC1091
source "${REPO_ROOT}/scripts/lib/terraform.sh"
# shellcheck disable=SC1091
source "${REPO_ROOT}/scripts/lib/aws-mfa.sh"
aegis_ensure_aws_mfa "${OTP}"

state_status=0
aegis_terraform_state_has_resources "${REPORTING_ROOT}" || state_status=$?
if [[ "${state_status}" -eq 1 ]]; then
  echo "Reporting Terraform state is accessible but empty. Nothing to destroy." >&2
  exit 0
elif [[ "${state_status}" -eq 2 ]]; then
  echo "Reporting Terraform state is not accessible. Refusing to assume it is safe to destroy." >&2
  exit 1
fi

cat >&2 <<'WARN'
[WARNING] Destroying reporting will:
  - Stop the daily factory report scheduler
  - Remove reporting Step Functions and Lambda resources
  - Preserve S3 processed input and generated reports in the data bucket

WARN

aegis_terraform_destroy_root "${REPO_ROOT}/infra/reporting"

echo ""
echo "Reporting resources destroyed. S3 data and report objects are preserved."
