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

if terraform -chdir="${REPO_ROOT}/infra/hub" output cluster_name >/dev/null 2>&1; then
  cd "${REPO_ROOT}/scripts/ansible"
  ansible-playbook -i inventory/hub_eks_dynamic.sh playbooks/hub_admin_ingress_cleanup.yml || true
else
  echo "Hub cluster output not available. Skipping Ansible ingress cleanup."
fi
