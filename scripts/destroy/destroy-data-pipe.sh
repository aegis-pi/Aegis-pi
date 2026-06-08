#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
OTP="${1:-}"
DATA_PIPE_ROOT="${REPO_ROOT}/infra/data-pipeline"

# shellcheck disable=SC1091
source "${REPO_ROOT}/scripts/lib/config.sh"
aegis_load_config "${REPO_ROOT}"
# shellcheck disable=SC1091
source "${REPO_ROOT}/scripts/lib/terraform.sh"
# shellcheck disable=SC1091
source "${REPO_ROOT}/scripts/lib/aws-mfa.sh"
aegis_ensure_aws_mfa "${OTP}"

state_status=0
aegis_terraform_state_has_resources "${DATA_PIPE_ROOT}" || state_status=$?
if [[ "${state_status}" -eq 1 ]]; then
  echo "Data-pipeline Terraform state is accessible but empty. Nothing to destroy." >&2
  exit 0
elif [[ "${state_status}" -eq 2 ]]; then
  echo "Data-pipeline Terraform state is not accessible. Refusing to assume it is safe to destroy." >&2
  exit 1
fi

cat >&2 <<'WARN'
[WARNING] Destroying data-pipeline will:
  - Stop IoT Rules → raw S3 ingestion halts immediately for all factories
  - Remove Lambda data processor → no new DynamoDB or S3 processed writes
  - Remove SnapshotPresigner API/Lambda → snapshot-uploader can no longer obtain presigned S3 PUT URLs
  - DynamoDB table and its data are preserved (managed by infra/foundation)

Recommended: stop dummy generators before proceeding.
  scripts/destroy/stop-dummy-generators.sh

WARN

aegis_terraform_destroy_root "${REPO_ROOT}/infra/data-pipeline"

echo ""
echo "Data-pipeline destroyed. DynamoDB data preserved in infra/foundation."
echo "Next steps for full teardown:"
echo "  1. scripts/destroy/stop-dummy-generators.sh   (if not already done)"
echo "  2. scripts/destroy/destroy-hub.sh"
