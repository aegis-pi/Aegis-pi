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

FORCE_ARGOCD_UPGRADE="${FORCE_ARGOCD_UPGRADE:-false}"
FORCE_GRAFANA_UPGRADE="${FORCE_GRAFANA_UPGRADE:-false}"
FORCE_AWS_LB_CONTROLLER_UPGRADE="${FORCE_AWS_LB_CONTROLLER_UPGRADE:-false}"
export GODEBUG="${GODEBUG:-http2client=0}"

cd "${REPO_ROOT}/scripts/ansible"
ansible-playbook \
  -i inventory/hub_eks_dynamic.sh \
  playbooks/hub_argocd_bootstrap.yml \
  -e "argocd_force_upgrade=${FORCE_ARGOCD_UPGRADE}"
ansible-playbook -i inventory/hub_eks_dynamic.sh playbooks/hub_argocd_verify.yml
ansible-playbook -i inventory/hub_eks_dynamic.sh playbooks/hub_prometheus_agent_cleanup.yml
ansible-playbook \
  -i inventory/hub_eks_dynamic.sh \
  playbooks/hub_grafana_bootstrap.yml \
  -e "grafana_force_upgrade=${FORCE_GRAFANA_UPGRADE}"
ansible-playbook -i inventory/hub_eks_dynamic.sh playbooks/hub_grafana_verify.yml
"${REPO_ROOT}/scripts/ops/export-hub-ui-credentials.sh" "${OTP}"
ansible-playbook \
  -i inventory/hub_eks_dynamic.sh \
  playbooks/hub_aws_load_balancer_controller_bootstrap.yml \
  -e "aws_lb_controller_force_upgrade=${FORCE_AWS_LB_CONTROLLER_UPGRADE}"
ansible-playbook -i inventory/hub_eks_dynamic.sh playbooks/hub_aws_load_balancer_controller_verify.yml
echo "Skipped Admin UI HTTPS Ingress. Run scripts/build/build-admin-ui-after-ns.sh after Route53 NS delegation."
echo "Skipped Hub-Spoke Tailscale and ApplicationSet. Run scripts/build/register-spoke-factory-a.sh, register-spoke-factory-b.sh, and register-spoke-factory-c.sh when each Spoke K3s API is reachable."
