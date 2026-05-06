#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
OTP="${1:-}"
FOUNDATION_STATE="${REPO_ROOT}/infra/foundation/terraform.tfstate"

# shellcheck disable=SC1091
source "${REPO_ROOT}/scripts/lib/config.sh"
aegis_load_config "${REPO_ROOT}"
# shellcheck disable=SC1091
source "${REPO_ROOT}/scripts/lib/aws-mfa.sh"
# shellcheck disable=SC1091
source "${REPO_ROOT}/scripts/lib/terraform.sh"

if [[ ! -f "${FOUNDATION_STATE}" ]]; then
  echo "Hub destroy requires ${FOUNDATION_STATE} because infra/hub reads foundation outputs for AMP/IRSA wiring." >&2
  echo "Restore the foundation state file before destroying hub resources." >&2
  exit 1
fi

aegis_ensure_aws_mfa "${OTP}"

if terraform -chdir="${REPO_ROOT}/infra/hub" output cluster_name >/dev/null 2>&1; then
  cd "${REPO_ROOT}/scripts/ansible"
  ansible-playbook -i inventory/hub_eks_dynamic.sh playbooks/hub_admin_ingress_cleanup.yml || true
fi

aegis_terraform_destroy_root "${REPO_ROOT}/infra/hub"
