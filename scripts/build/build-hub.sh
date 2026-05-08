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
FORCE_AWS_LB_CONTROLLER_UPGRADE="${FORCE_AWS_LB_CONTROLLER_UPGRADE:-false}"
FORCE_TAILSCALE_OPERATOR_UPGRADE="${FORCE_TAILSCALE_OPERATOR_UPGRADE:-false}"
BUILD_TAILSCALE="${BUILD_TAILSCALE:-true}"

aegis_terraform_apply_root "${REPO_ROOT}/infra/hub"
"${REPO_ROOT}/scripts/ops/admin-ui-nameservers.sh"

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
ansible-playbook \
  -i inventory/hub_eks_dynamic.sh \
  playbooks/hub_aws_load_balancer_controller_bootstrap.yml \
  -e "aws_lb_controller_force_upgrade=${FORCE_AWS_LB_CONTROLLER_UPGRADE}"
ansible-playbook -i inventory/hub_eks_dynamic.sh playbooks/hub_aws_load_balancer_controller_verify.yml
ansible-playbook -i inventory/hub_eks_dynamic.sh playbooks/hub_admin_ingress_bootstrap.yml
ansible-playbook -i inventory/hub_eks_dynamic.sh playbooks/hub_admin_ingress_verify.yml
if [[ "${BUILD_TAILSCALE}" == "true" ]]; then
  ansible-playbook \
    -i inventory/hub_eks_dynamic.sh \
    playbooks/hub_tailscale_bootstrap.yml \
    -e "tailscale_operator_force_upgrade=${FORCE_TAILSCALE_OPERATOR_UPGRADE}"
  ansible-playbook -i inventory/hub_eks_dynamic.sh playbooks/hub_tailscale_verify.yml
else
  echo "Skipped Hub Tailscale bootstrap/verify. Set BUILD_TAILSCALE=true to enable it."
fi
