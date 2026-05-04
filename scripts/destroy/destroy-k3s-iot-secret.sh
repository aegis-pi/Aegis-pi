#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# shellcheck disable=SC1091
source "${REPO_ROOT}/scripts/lib/config.sh"
aegis_load_config "${REPO_ROOT}"

FACTORY_ID="${FACTORY_ID:-${AEGIS_FACTORY_ID}}"
REMOTE_USER="${REMOTE_USER:-${AEGIS_FACTORY_A_SSH_USER}}"
REMOTE_HOST="${REMOTE_HOST:-${AEGIS_FACTORY_A_MASTER_HOST}}"
K8S_NAMESPACE="${K8S_NAMESPACE:-${AEGIS_K8S_IOT_NAMESPACE}}"
K8S_SECRET_NAME="${K8S_SECRET_NAME:-${AEGIS_K8S_IOT_SECRET_PREFIX}-${FACTORY_ID}${AEGIS_K8S_IOT_SECRET_SUFFIX}}"

cd "${REPO_ROOT}"

ssh "${REMOTE_USER}@${REMOTE_HOST}" "
set -euo pipefail
kubectl -n '${K8S_NAMESPACE}' delete secret '${K8S_SECRET_NAME}' --ignore-not-found=true
"

echo "Deleted K3s Secret ${K8S_NAMESPACE}/${K8S_SECRET_NAME} if it existed."
