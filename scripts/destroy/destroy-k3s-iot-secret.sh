#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

FACTORY_ID="${FACTORY_ID:-factory-a}"
REMOTE_USER="${REMOTE_USER:-vicbear}"
REMOTE_HOST="${REMOTE_HOST:-10.10.10.10}"
K8S_NAMESPACE="${K8S_NAMESPACE:-edge-system}"
K8S_SECRET_NAME="${K8S_SECRET_NAME:-${FACTORY_ID}-iot-cert}"

cd "${REPO_ROOT}"

ssh "${REMOTE_USER}@${REMOTE_HOST}" "
set -euo pipefail
kubectl -n '${K8S_NAMESPACE}' delete secret '${K8S_SECRET_NAME}' --ignore-not-found=true
"

echo "Deleted K3s Secret ${K8S_NAMESPACE}/${K8S_SECRET_NAME} if it existed."
