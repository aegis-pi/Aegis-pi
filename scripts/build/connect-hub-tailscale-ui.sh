#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
OTP="${1:-}"
FORCE_TAILSCALE_OPERATOR_UPGRADE="${FORCE_TAILSCALE_OPERATOR_UPGRADE:-false}"
HUB_TERRAFORM_STATE="${REPO_ROOT}/infra/hub/terraform.tfstate"

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "missing required command: $1" >&2
    exit 1
  fi
}

cd "${REPO_ROOT}"

# shellcheck disable=SC1091
source "${REPO_ROOT}/scripts/lib/config.sh"
aegis_load_config "${REPO_ROOT}"
# shellcheck disable=SC1091
source "${REPO_ROOT}/scripts/lib/aws-mfa.sh"
aegis_ensure_aws_mfa "${OTP}"

for command_name in aws ansible-playbook kubectl helm jq curl; do
  require_command "${command_name}"
done

if [[ ! -f "${HUB_TERRAFORM_STATE}" ]]; then
  echo "Missing ${HUB_TERRAFORM_STATE}. Run scripts/build/build-hub.sh first." >&2
  exit 1
fi

export AEGIS_TAILSCALE_UI_ENABLED=true
export AEGIS_TAILSCALE_SPOKE_REGISTRATION_ENABLED=false
export AEGIS_FACTORY_A_ENABLED=false
export AEGIS_FACTORY_B_ENABLED=false
export AEGIS_FACTORY_C_ENABLED=false
export FORCE_TAILSCALE_OPERATOR_UPGRADE

cd "${REPO_ROOT}/scripts/ansible"
ansible-playbook \
  -i inventory/hub_eks_dynamic.sh \
  playbooks/hub_tailscale_bootstrap.yml \
  -e "tailscale_operator_force_upgrade=${FORCE_TAILSCALE_OPERATOR_UPGRADE}"
ansible-playbook -i inventory/hub_eks_dynamic.sh playbooks/hub_tailscale_verify.yml

echo "Hub Tailscale UI connection completed."
