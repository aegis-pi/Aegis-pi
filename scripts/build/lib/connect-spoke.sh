#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${FACTORY_TARGET:-}" ]]; then
  echo "FACTORY_TARGET is required: factory-a, factory-b, or factory-c" >&2
  exit 1
fi

case "${FACTORY_TARGET}" in
  factory-a)
    export AEGIS_FACTORY_A_ENABLED=true
    export AEGIS_FACTORY_B_ENABLED=false
    export AEGIS_FACTORY_C_ENABLED=false
    APP_NAME=aegis-spoke-factory-a
    ;;
  factory-b)
    export AEGIS_FACTORY_A_ENABLED=false
    export AEGIS_FACTORY_B_ENABLED=true
    export AEGIS_FACTORY_C_ENABLED=false
    APP_NAME=aegis-spoke-factory-b
    ;;
  factory-c)
    export AEGIS_FACTORY_A_ENABLED=false
    export AEGIS_FACTORY_B_ENABLED=false
    export AEGIS_FACTORY_C_ENABLED=true
    APP_NAME=aegis-spoke-factory-c
    ;;
  *)
    echo "Unsupported FACTORY_TARGET=${FACTORY_TARGET}; expected factory-a, factory-b, or factory-c" >&2
    exit 1
    ;;
esac

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
OTP="${1:-}"
FORCE_TAILSCALE_OPERATOR_UPGRADE="${FORCE_TAILSCALE_OPERATOR_UPGRADE:-false}"
HUB_ONLY_RECONNECT="${HUB_ONLY_RECONNECT:-false}"
if [[ "${HUB_ONLY_RECONNECT}" == "true" ]]; then
  SYNC_SPOKE_APP="${SYNC_SPOKE_APP:-false}"
  REFRESH_SPOKE_ECR_PULL_SECRET="${REFRESH_SPOKE_ECR_PULL_SECRET:-false}"
  RESTART_SPOKE_AFTER_ECR_SECRET_REFRESH="${RESTART_SPOKE_AFTER_ECR_SECRET_REFRESH:-false}"
else
  SYNC_SPOKE_APP="${SYNC_SPOKE_APP:-true}"
  REFRESH_SPOKE_ECR_PULL_SECRET="${REFRESH_SPOKE_ECR_PULL_SECRET:-true}"
  RESTART_SPOKE_AFTER_ECR_SECRET_REFRESH="${RESTART_SPOKE_AFTER_ECR_SECRET_REFRESH:-true}"
fi
ARGOCD_APP_NAMESPACE="${ARGOCD_APP_NAMESPACE:-argocd}"
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

if [[ "${SYNC_SPOKE_APP}" == "true" ]]; then
  require_command argocd
fi

if [[ ! -f "${HUB_TERRAFORM_STATE}" ]]; then
  echo "Missing ${HUB_TERRAFORM_STATE}. Run scripts/build/build-hub.sh first." >&2
  exit 1
fi

export AEGIS_TAILSCALE_UI_ENABLED=false
export AEGIS_TAILSCALE_SPOKE_REGISTRATION_ENABLED=true
export FORCE_TAILSCALE_OPERATOR_UPGRADE

if [[ "${HUB_ONLY_RECONNECT}" == "true" ]]; then
  cat <<EOF
Hub-only reconnect mode enabled for ${FACTORY_TARGET}.
  SYNC_SPOKE_APP=${SYNC_SPOKE_APP}
  REFRESH_SPOKE_ECR_PULL_SECRET=${REFRESH_SPOKE_ECR_PULL_SECRET}
  RESTART_SPOKE_AFTER_ECR_SECRET_REFRESH=${RESTART_SPOKE_AFTER_ECR_SECRET_REFRESH}

This mode recreates the Hub-side Tailscale/ApplicationSet control path without
forcing an ArgoCD sync or Spoke rollout by default.
EOF
fi

cd "${REPO_ROOT}/scripts/ansible"
ansible-playbook \
  -i inventory/hub_eks_dynamic.sh \
  playbooks/hub_tailscale_bootstrap.yml \
  -e "tailscale_operator_force_upgrade=${FORCE_TAILSCALE_OPERATOR_UPGRADE}"
ansible-playbook -i inventory/hub_eks_dynamic.sh playbooks/hub_tailscale_verify.yml
ansible-playbook -i inventory/hub_eks_dynamic.sh playbooks/hub_aegis_spoke_applicationset_bootstrap.yml
ansible-playbook -i inventory/hub_eks_dynamic.sh playbooks/hub_aegis_spoke_applicationset_verify.yml

cd "${REPO_ROOT}"

if [[ "${FACTORY_TARGET}" == "factory-a" && "${REFRESH_SPOKE_ECR_PULL_SECRET}" == "true" ]]; then
  FACTORY_A_KUBECONFIG_FILE="${AEGIS_FACTORY_A_DIRECT_KUBECONFIG:-${HOME}/Aegis/.aegis/secrets/kubeconfig/factory-a.tailscale-ip-tlsname.kubeconfig}"
  FACTORY_A_KUBECONFIG="${AEGIS_FACTORY_A_DIRECT_KUBECONFIG:-${HOME}/Aegis/.aegis/secrets/kubeconfig/factory-a.tailscale-ip-tlsname.kubeconfig}" \
  ECR_PULL_SECRET_NAMESPACE="${ECR_PULL_SECRET_NAMESPACE:-ai-apps}" \
  ECR_PULL_SECRET_NAME="${ECR_PULL_SECRET_NAME:-ecr-registry}" \
    "${REPO_ROOT}/scripts/ops/refresh-factory-a-ecr-pull-secret.sh" "${OTP}"

  if [[ "${RESTART_SPOKE_AFTER_ECR_SECRET_REFRESH}" == "true" ]]; then
    for deployment in \
      aegis-spoke-factory-a-log-adapter \
      aegis-spoke-edge-iot-publisher \
      aegis-spoke-snapshot-uploader; do
      kubectl --kubeconfig "${FACTORY_A_KUBECONFIG_FILE}" \
        -n "${ECR_PULL_SECRET_NAMESPACE:-ai-apps}" \
        rollout restart "deployment/${deployment}" 2>/dev/null || true
    done
  fi
elif [[ "${REFRESH_SPOKE_ECR_PULL_SECRET}" != "true" ]]; then
  echo "Skipped ${FACTORY_TARGET} ECR pull secret refresh. Set REFRESH_SPOKE_ECR_PULL_SECRET=true to enable it."
fi

if [[ "${SYNC_SPOKE_APP}" == "true" ]]; then
  ARGOCD_CORE_KUBECONFIG="$(mktemp)"
  cleanup_argocd_core_kubeconfig() {
    rm -f "${ARGOCD_CORE_KUBECONFIG}"
  }
  trap cleanup_argocd_core_kubeconfig EXIT

  kubectl config view --raw >"${ARGOCD_CORE_KUBECONFIG}"
  KUBECONFIG="${ARGOCD_CORE_KUBECONFIG}" kubectl config set-context --current --namespace="${ARGOCD_APP_NAMESPACE}" >/dev/null

  KUBECONFIG="${ARGOCD_CORE_KUBECONFIG}" argocd --core app sync "${APP_NAME}" --app-namespace "${ARGOCD_APP_NAMESPACE}" --timeout 300
  KUBECONFIG="${ARGOCD_CORE_KUBECONFIG}" argocd --core app wait "${APP_NAME}" --app-namespace "${ARGOCD_APP_NAMESPACE}" --sync --health --timeout 300
else
  echo "Skipped ${APP_NAME} sync/wait. Set SYNC_SPOKE_APP=true to enable it."
fi

echo "${FACTORY_TARGET} Hub ArgoCD cluster registration completed."
