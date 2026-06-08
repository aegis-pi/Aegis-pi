#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
OTP="${1:-}"
FACTORY_ID="${FACTORY_ID:-}"

cd "${REPO_ROOT}"

# shellcheck disable=SC1091
source "${REPO_ROOT}/scripts/lib/config.sh"
aegis_load_config "${REPO_ROOT}"

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "missing required command: $1" >&2
    exit 1
  fi
}

require_command aws

# shellcheck disable=SC1091
source "${REPO_ROOT}/scripts/lib/aws-mfa.sh"
aegis_ensure_aws_mfa "${OTP}"
# shellcheck disable=SC1091
source "${REPO_ROOT}/scripts/lib/terraform.sh"

FACTORY_ID="${FACTORY_ID:-${AEGIS_FACTORY_ID}}"
export FACTORY_ID
BUILD_TAILSCALE="${BUILD_TAILSCALE:-true}"
DEPLOY_SPOKES="${DEPLOY_SPOKES:-${BUILD_TAILSCALE}}"
FORCE_TAILSCALE_OPERATOR_UPGRADE="${FORCE_TAILSCALE_OPERATOR_UPGRADE:-false}"
HUB_TERRAFORM_ROOT="${REPO_ROOT}/infra/hub"
TAILSCALE_OPERATOR_ENV="${AEGIS_TAILSCALE_OPERATOR_ENV:-${HOME}/Aegis/.aegis/secrets/tailscale/operator.env}"
FACTORY_A_DIRECT_KUBECONFIG="${AEGIS_FACTORY_A_DIRECT_KUBECONFIG:-${HOME}/Aegis/.aegis/secrets/kubeconfig/factory-a.tailscale-ip-tlsname.kubeconfig}"
export AEGIS_FACTORY_A_ENABLED="${AEGIS_FACTORY_A_ENABLED:-true}"
export AEGIS_FACTORY_B_ENABLED="${AEGIS_FACTORY_B_ENABLED:-false}"
export AEGIS_FACTORY_C_ENABLED="${AEGIS_FACTORY_C_ENABLED:-false}"

for command_name in jq curl ssh scp; do
  require_command "${command_name}"
done

if [[ "${BUILD_TAILSCALE}" == "true" || "${DEPLOY_SPOKES}" == "true" ]]; then
  aegis_terraform_require_state_resources "${HUB_TERRAFORM_ROOT}" "hub"
fi

if [[ "${BUILD_TAILSCALE}" == "true" ]]; then
  for command_name in ansible-playbook kubectl helm jq; do
    require_command "${command_name}"
  done
  if [[ ! -f "${TAILSCALE_OPERATOR_ENV}" ]]; then
    echo "Missing ${TAILSCALE_OPERATOR_ENV}. Set BUILD_TAILSCALE=false to skip Hub-Spoke Tailscale bootstrap." >&2
    exit 1
  fi
  if ! env -i bash -c "set -euo pipefail; set -a; . \"${TAILSCALE_OPERATOR_ENV}\"; test -n \"\${TAILSCALE_OAUTH_CLIENT_ID:-}\"; test -n \"\${TAILSCALE_OAUTH_CLIENT_SECRET:-}\"" >/dev/null 2>&1; then
    echo "${TAILSCALE_OPERATOR_ENV} must define TAILSCALE_OAUTH_CLIENT_ID and TAILSCALE_OAUTH_CLIENT_SECRET" >&2
    exit 1
  fi
  if [[ ! -f "${FACTORY_A_DIRECT_KUBECONFIG}" ]]; then
    echo "Missing ${FACTORY_A_DIRECT_KUBECONFIG}. Set BUILD_TAILSCALE=false to skip factory-a ArgoCD cluster Secret bootstrap." >&2
    exit 1
  fi
elif [[ "${DEPLOY_SPOKES}" == "true" ]]; then
  for command_name in ansible-playbook kubectl jq; do
    require_command "${command_name}"
  done
fi

scripts/iot/register-thing.sh "${OTP}"
scripts/iot/register-k3s-secret.sh

if [[ "${BUILD_TAILSCALE}" == "true" ]]; then
  cd "${REPO_ROOT}/scripts/ansible"
  ansible-playbook \
    -i inventory/hub_eks_dynamic.sh \
    playbooks/hub_tailscale_bootstrap.yml \
    -e "tailscale_operator_force_upgrade=${FORCE_TAILSCALE_OPERATOR_UPGRADE}"
  ansible-playbook -i inventory/hub_eks_dynamic.sh playbooks/hub_tailscale_verify.yml
  cd "${REPO_ROOT}"
else
  echo "Skipped Hub-Spoke Tailscale bootstrap/verify. Set BUILD_TAILSCALE=true to enable it."
fi

if [[ "${DEPLOY_SPOKES}" == "true" ]]; then
  cd "${REPO_ROOT}/scripts/ansible"
  ansible-playbook -i inventory/hub_eks_dynamic.sh playbooks/hub_aegis_spoke_applicationset_bootstrap.yml
  ansible-playbook -i inventory/hub_eks_dynamic.sh playbooks/hub_aegis_spoke_applicationset_verify.yml
else
  echo "Skipped AEGIS Spoke ApplicationSet deploy. Set DEPLOY_SPOKES=true to enable it."
fi
