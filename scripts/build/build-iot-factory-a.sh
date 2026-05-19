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
# shellcheck disable=SC1091
source "${REPO_ROOT}/scripts/lib/aws-mfa.sh"
aegis_ensure_aws_mfa "${OTP}"

FACTORY_ID="${FACTORY_ID:-${AEGIS_FACTORY_ID}}"
export FACTORY_ID
DEPLOY_SPOKES="${DEPLOY_SPOKES:-true}"

scripts/iot/register-thing.sh "${OTP}"
scripts/iot/register-k3s-secret.sh

if [[ "${DEPLOY_SPOKES}" == "true" ]]; then
  cd "${REPO_ROOT}/scripts/ansible"
  ansible-playbook -i inventory/hub_eks_dynamic.sh playbooks/hub_aegis_spoke_applicationset_bootstrap.yml
  ansible-playbook -i inventory/hub_eks_dynamic.sh playbooks/hub_aegis_spoke_applicationset_verify.yml
else
  echo "Skipped AEGIS Spoke ApplicationSet deploy. Set DEPLOY_SPOKES=true to enable it."
fi
