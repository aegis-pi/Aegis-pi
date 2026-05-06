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
SECRET_NAME="${GRAFANA_ADMIN_SECRET:-${AEGIS_GRAFANA_ADMIN_SECRET}}"
OTP="${1:-}"

# shellcheck disable=SC1091
source "${REPO_ROOT}/scripts/lib/aws-mfa.sh"
AWS_REGION="${REGION}" aegis_ensure_aws_mfa "${OTP}"
export AWS_REGION="${REGION}"
export AWS_DEFAULT_REGION="${AWS_DEFAULT_REGION:-${AWS_REGION}}"

aws eks update-kubeconfig --region "$REGION" --name "$CLUSTER_NAME"

kubectl -n "$NAMESPACE" get secret "$SECRET_NAME" \
  -o jsonpath='{.data.admin-password}' | base64 -d
echo
