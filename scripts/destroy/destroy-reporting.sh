#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
OTP="${1:-}"
REPORTING_STATE="${REPO_ROOT}/infra/reporting/terraform.tfstate"

# shellcheck disable=SC1091
source "${REPO_ROOT}/scripts/lib/config.sh"
aegis_load_config "${REPO_ROOT}"

if [[ ! -f "${REPORTING_STATE}" ]]; then
  echo "No infra/reporting/terraform.tfstate found. Nothing to destroy." >&2
  exit 0
fi

cat >&2 <<'WARN'
[WARNING] Destroying reporting will:
  - Stop the daily factory report scheduler
  - Remove reporting Step Functions and Lambda resources
  - Preserve S3 processed input and generated reports in the data bucket

WARN

# shellcheck disable=SC1091
source "${REPO_ROOT}/scripts/lib/aws-mfa.sh"
# shellcheck disable=SC1091
source "${REPO_ROOT}/scripts/lib/terraform.sh"
aegis_ensure_aws_mfa "${OTP}"

aegis_terraform_destroy_root "${REPO_ROOT}/infra/reporting"

echo ""
echo "Reporting resources destroyed. S3 data and report objects are preserved."

