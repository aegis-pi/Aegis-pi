#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# shellcheck disable=SC1091
source "${REPO_ROOT}/scripts/lib/config.sh"
aegis_load_config "${REPO_ROOT}"

REGION="${AWS_REGION:-${AEGIS_AWS_REGION}}"
CLUSTER_NAME="${CLUSTER_NAME:-${AEGIS_HUB_CLUSTER_NAME}}"
NAMESPACE="${GRAFANA_NAMESPACE:-${AEGIS_GRAFANA_NAMESPACE}}"
LOCAL_PORT="${GRAFANA_LOCAL_PORT:-${AEGIS_GRAFANA_LOCAL_PORT}}"
REMOTE_PORT="${GRAFANA_REMOTE_PORT:-${AEGIS_GRAFANA_REMOTE_PORT}}"
SECRET_NAME="${GRAFANA_ADMIN_SECRET:-${AEGIS_GRAFANA_ADMIN_SECRET}}"
PRINT_PASSWORD="false"

usage() {
  cat <<USAGE
Usage: $0 [--print-password]

Environment:
  AWS_REGION            AWS region. Default: ${AEGIS_AWS_REGION}
  CLUSTER_NAME          EKS cluster name. Default: ${AEGIS_HUB_CLUSTER_NAME}
  GRAFANA_NAMESPACE     Grafana namespace. Default: ${AEGIS_GRAFANA_NAMESPACE}
  GRAFANA_LOCAL_PORT    Local port. Default: ${AEGIS_GRAFANA_LOCAL_PORT}
  GRAFANA_REMOTE_PORT   Grafana service port. Default: ${AEGIS_GRAFANA_REMOTE_PORT}
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
  deployment/grafana

if [[ "$PRINT_PASSWORD" == "true" ]]; then
  kubectl -n "$NAMESPACE" get secret "$SECRET_NAME" \
    -o jsonpath='{.data.admin-password}' | base64 -d
  echo
fi

echo "Grafana UI: http://127.0.0.1:${LOCAL_PORT}"
kubectl -n "$NAMESPACE" port-forward \
  service/grafana \
  "${LOCAL_PORT}:${REMOTE_PORT}"
