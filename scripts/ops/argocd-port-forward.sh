#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# shellcheck disable=SC1091
source "${REPO_ROOT}/scripts/lib/config.sh"
aegis_load_config "${REPO_ROOT}"

REGION="${AWS_REGION:-${AEGIS_AWS_REGION}}"
CLUSTER_NAME="${CLUSTER_NAME:-${AEGIS_HUB_CLUSTER_NAME}}"
NAMESPACE="${ARGOCD_NAMESPACE:-${AEGIS_ARGOCD_NAMESPACE}}"
LOCAL_PORT="${ARGOCD_LOCAL_PORT:-${AEGIS_ARGOCD_LOCAL_PORT}}"
REMOTE_PORT="${ARGOCD_REMOTE_PORT:-${AEGIS_ARGOCD_REMOTE_PORT}}"
PRINT_PASSWORD="false"

usage() {
  cat <<USAGE
Usage: $0 [--print-password]

Environment:
  AWS_REGION           AWS region. Default: ${AEGIS_AWS_REGION}
  CLUSTER_NAME         EKS cluster name. Default: ${AEGIS_HUB_CLUSTER_NAME}
  ARGOCD_NAMESPACE     ArgoCD namespace. Default: ${AEGIS_ARGOCD_NAMESPACE}
  ARGOCD_LOCAL_PORT    Local port. Default: ${AEGIS_ARGOCD_LOCAL_PORT}
  ARGOCD_REMOTE_PORT   ArgoCD service port. Default: ${AEGIS_ARGOCD_REMOTE_PORT}
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --print-password)
      PRINT_PASSWORD="true"
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

aws eks update-kubeconfig --region "$REGION" --name "$CLUSTER_NAME"

kubectl -n "$NAMESPACE" wait \
  --for=condition=available \
  --timeout=180s \
  deployment/argocd-server

if [[ "$PRINT_PASSWORD" == "true" ]]; then
  kubectl -n "$NAMESPACE" get secret argocd-initial-admin-secret \
    -o jsonpath='{.data.password}' | base64 -d
  echo
fi

echo "ArgoCD UI: https://127.0.0.1:${LOCAL_PORT}"
kubectl -n "$NAMESPACE" port-forward \
  service/argocd-server \
  "${LOCAL_PORT}:${REMOTE_PORT}"
