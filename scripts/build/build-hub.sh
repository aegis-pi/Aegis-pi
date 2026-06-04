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
aegis_ensure_aws_mfa "${OTP}"

"${SCRIPT_DIR}/build-hub-infra.sh" "${OTP}"

RECONCILE_DATA_PIPE_EKS_ACCESS="${RECONCILE_DATA_PIPE_EKS_ACCESS:-true}"
SLOW_COLLECTOR_ROLE_NAME="AEGIS-IAMRole-Lambda-CloudInfraSlowCollector"
DATA_PIPE_STATE="${REPO_ROOT}/infra/data-pipeline/terraform.tfstate"

if [[ "${RECONCILE_DATA_PIPE_EKS_ACCESS}" != "true" ]]; then
  echo "Skipped data-pipeline EKS access reconcile (RECONCILE_DATA_PIPE_EKS_ACCESS=${RECONCILE_DATA_PIPE_EKS_ACCESS})."
elif ROLE_LOOKUP_OUTPUT="$(aws iam get-role --role-name "${SLOW_COLLECTOR_ROLE_NAME}" --query Role.RoleName --output text 2>&1)"; then
  if [[ ! -f "${DATA_PIPE_STATE}" ]]; then
    echo "SlowCollector IAM role exists, but data-pipeline Terraform state is missing: ${DATA_PIPE_STATE}" >&2
    echo "Restore the state before reconciling EKS access, or set RECONCILE_DATA_PIPE_EKS_ACCESS=false to skip." >&2
    exit 1
  fi
  "${SCRIPT_DIR}/reconcile-data-pipe-eks-access.sh" "${OTP}"
elif [[ "${ROLE_LOOKUP_OUTPUT}" == *"NoSuchEntity"* ]]; then
  echo "Skipped data-pipeline EKS access reconcile; SlowCollector IAM role does not exist yet."
else
  echo "Failed to check SlowCollector IAM role before EKS access reconcile:" >&2
  echo "${ROLE_LOOKUP_OUTPUT}" >&2
  exit 1
fi

"${SCRIPT_DIR}/build-hub-platform.sh" "${OTP}"
