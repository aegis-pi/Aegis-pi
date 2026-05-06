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
FORCE_ARGOCD_UPGRADE="${FORCE_ARGOCD_UPGRADE:-false}"
FORCE_GRAFANA_UPGRADE="${FORCE_GRAFANA_UPGRADE:-false}"

aegis_terraform_apply_root "${REPO_ROOT}/infra/hub"

cd "${REPO_ROOT}/scripts/ansible"
ansible-playbook \
  -i inventory/hub_eks_dynamic.sh \
  playbooks/hub_argocd_bootstrap.yml \
  -e "argocd_force_upgrade=${FORCE_ARGOCD_UPGRADE}"
ansible-playbook -i inventory/hub_eks_dynamic.sh playbooks/hub_argocd_verify.yml
ansible-playbook -i inventory/hub_eks_dynamic.sh playbooks/hub_prometheus_agent_bootstrap.yml
ansible-playbook -i inventory/hub_eks_dynamic.sh playbooks/hub_prometheus_agent_verify.yml
ansible-playbook \
  -i inventory/hub_eks_dynamic.sh \
  playbooks/hub_grafana_bootstrap.yml \
  -e "grafana_force_upgrade=${FORCE_GRAFANA_UPGRADE}"
ansible-playbook -i inventory/hub_eks_dynamic.sh playbooks/hub_grafana_verify.yml
