#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# shellcheck disable=SC1091
source "${REPO_ROOT}/scripts/lib/config.sh"
aegis_load_config "${REPO_ROOT}"

REGION="${AWS_REGION:-${AEGIS_AWS_REGION}}"
REGISTRY="${ECR_REGISTRY:-611058323802.dkr.ecr.${REGION}.amazonaws.com}"
NAMESPACE="${ECR_PULL_SECRET_NAMESPACE:-aegis-spoke-system}"
SECRET_NAME="${ECR_PULL_SECRET_NAME:-ecr-registry}"
KUBECONFIG_FILE="${FACTORY_A_KUBECONFIG:-${HOME}/Aegis/.aegis/secrets/kubeconfig/factory-a.tailscale-ip-tlsname.kubeconfig}"
OTP="${1:-}"

usage() {
  cat <<'USAGE'
Usage: scripts/ops/refresh-factory-a-ecr-pull-secret.sh [MFA_OTP]

Creates or updates factory-a Kubernetes docker-registry Secret for ECR pulls.
Defaults:
  namespace: aegis-spoke-system
  secret:    ecr-registry
USAGE
}

if [[ "${OTP}" == "-h" || "${OTP}" == "--help" ]]; then
  usage
  exit 0
fi

# shellcheck disable=SC1091
source "${REPO_ROOT}/scripts/lib/aws-mfa.sh"
AWS_REGION="${REGION}" aegis_ensure_aws_mfa "${OTP}"
export AWS_REGION="${REGION}"
export AWS_DEFAULT_REGION="${AWS_DEFAULT_REGION:-${AWS_REGION}}"

if [[ ! -f "${KUBECONFIG_FILE}" ]]; then
  echo "Missing factory-a kubeconfig: ${KUBECONFIG_FILE}" >&2
  exit 1
fi

password="$(aws ecr get-login-password --region "${REGION}")"

kubectl --kubeconfig "${KUBECONFIG_FILE}" get namespace "${NAMESPACE}" >/dev/null 2>&1 || \
  kubectl --kubeconfig "${KUBECONFIG_FILE}" create namespace "${NAMESPACE}"

kubectl --kubeconfig "${KUBECONFIG_FILE}" -n "${NAMESPACE}" create secret docker-registry "${SECRET_NAME}" \
  --docker-server="${REGISTRY}" \
  --docker-username=AWS \
  --docker-password="${password}" \
  --dry-run=client \
  -o yaml | kubectl --kubeconfig "${KUBECONFIG_FILE}" apply -f -

echo "ECR pull secret ${NAMESPACE}/${SECRET_NAME} refreshed for ${REGISTRY}"
