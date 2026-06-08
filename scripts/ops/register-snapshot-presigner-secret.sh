#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# shellcheck disable=SC1091
source "${REPO_ROOT}/scripts/lib/config.sh"
aegis_load_config "${REPO_ROOT}"

REMOTE_USER="${REMOTE_USER:-${AEGIS_FACTORY_A_SSH_USER}}"
REMOTE_HOST="${REMOTE_HOST:-${AEGIS_FACTORY_A_MASTER_HOST}}"
K8S_NAMESPACE="${K8S_NAMESPACE:-ai-apps}"
K8S_SECRET_NAME="${K8S_SECRET_NAME:-snapshot-uploader-presign}"
PRESIGN_ENDPOINT="${PRESIGN_ENDPOINT:-}"
PRESIGN_TOKEN="${PRESIGN_TOKEN:-}"

if [[ -z "${PRESIGN_ENDPOINT}" ]]; then
  echo "PRESIGN_ENDPOINT is required" >&2
  echo "Example: PRESIGN_ENDPOINT=https://abc.execute-api.ap-south-1.amazonaws.com/image-snapshot/presign $0" >&2
  exit 1
fi

PRESIGN_ENDPOINT_B64="$(printf '%s' "${PRESIGN_ENDPOINT}" | base64 | tr -d '\n')"
PRESIGN_TOKEN_B64="$(printf '%s' "${PRESIGN_TOKEN}" | base64 | tr -d '\n')"

echo "Target: ${REMOTE_USER}@${REMOTE_HOST}"
echo "Namespace: ${K8S_NAMESPACE}"
echo "Secret: ${K8S_SECRET_NAME}"

ssh "${REMOTE_USER}@${REMOTE_HOST}" "
set -euo pipefail

presign_endpoint=\"\$(printf '%s' '${PRESIGN_ENDPOINT_B64}' | base64 -d)\"
presign_token=\"\$(printf '%s' '${PRESIGN_TOKEN_B64}' | base64 -d)\"

kubectl get namespace '${K8S_NAMESPACE}' >/dev/null 2>&1 || kubectl create namespace '${K8S_NAMESPACE}'

kubectl -n '${K8S_NAMESPACE}' create secret generic '${K8S_SECRET_NAME}' \
  --from-literal=endpoint=\"\${presign_endpoint}\" \
  --from-literal=token=\"\${presign_token}\" \
  --dry-run=client -o yaml | kubectl apply -f -

kubectl -n '${K8S_NAMESPACE}' get secret '${K8S_SECRET_NAME}'
"

echo "Registered K3s Secret ${K8S_NAMESPACE}/${K8S_SECRET_NAME}"
