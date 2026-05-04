#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# shellcheck disable=SC1091
source "${REPO_ROOT}/scripts/lib/config.sh"
aegis_load_config "${REPO_ROOT}"

FACTORY_ID="${FACTORY_ID:-${AEGIS_FACTORY_ID}}"
SECRET_DIR="${SECRET_DIR:-${REPO_ROOT}/secret/iot/${FACTORY_ID}}"
REMOTE_USER="${REMOTE_USER:-${AEGIS_FACTORY_A_SSH_USER}}"
REMOTE_HOST="${REMOTE_HOST:-${AEGIS_FACTORY_A_MASTER_HOST}}"
REMOTE_DIR="${REMOTE_DIR:-/tmp/aegis-iot-${FACTORY_ID}}"
K8S_NAMESPACE="${K8S_NAMESPACE:-${AEGIS_K8S_IOT_NAMESPACE}}"
K8S_SECRET_NAME="${K8S_SECRET_NAME:-${AEGIS_K8S_IOT_SECRET_PREFIX}-${FACTORY_ID}${AEGIS_K8S_IOT_SECRET_SUFFIX}}"

required_files=(
  "certificate.pem.crt"
  "private.pem.key"
  "AmazonRootCA1.pem"
  "endpoint.txt"
)

for file in "${required_files[@]}"; do
  if [[ ! -f "${SECRET_DIR}/${file}" ]]; then
    echo "missing required secret file: ${SECRET_DIR}/${file}" >&2
    exit 1
  fi
done

echo "Target: ${REMOTE_USER}@${REMOTE_HOST}"
echo "Namespace: ${K8S_NAMESPACE}"
echo "Secret: ${K8S_SECRET_NAME}"
echo "Local secret dir: ${SECRET_DIR}"

ssh "${REMOTE_USER}@${REMOTE_HOST}" "rm -rf '${REMOTE_DIR}' && mkdir -p '${REMOTE_DIR}' && chmod 700 '${REMOTE_DIR}'"

scp \
  "${SECRET_DIR}/certificate.pem.crt" \
  "${SECRET_DIR}/private.pem.key" \
  "${SECRET_DIR}/AmazonRootCA1.pem" \
  "${SECRET_DIR}/endpoint.txt" \
  "${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_DIR}/"

ssh "${REMOTE_USER}@${REMOTE_HOST}" "
set -euo pipefail

kubectl create namespace '${K8S_NAMESPACE}' --dry-run=client -o yaml | kubectl apply -f -

kubectl -n '${K8S_NAMESPACE}' create secret generic '${K8S_SECRET_NAME}' \
  --from-file=certificate.pem.crt='${REMOTE_DIR}/certificate.pem.crt' \
  --from-file=private.pem.key='${REMOTE_DIR}/private.pem.key' \
  --from-file=AmazonRootCA1.pem='${REMOTE_DIR}/AmazonRootCA1.pem' \
  --from-file=endpoint.txt='${REMOTE_DIR}/endpoint.txt' \
  --dry-run=client -o yaml | kubectl apply -f -

rm -rf '${REMOTE_DIR}'

kubectl -n '${K8S_NAMESPACE}' get secret '${K8S_SECRET_NAME}'
"

echo "Registered K3s Secret ${K8S_NAMESPACE}/${K8S_SECRET_NAME}"
