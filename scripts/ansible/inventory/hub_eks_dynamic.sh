#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
HUB_TERRAFORM_DIR="${HUB_TERRAFORM_DIR:-${REPO_ROOT}/infra/hub}"

# shellcheck disable=SC1091
source "${REPO_ROOT}/scripts/lib/config.sh"
aegis_load_config "${REPO_ROOT}"

if [[ "${1:-}" != "--list" && "${1:-}" != "" ]]; then
  echo '{"_meta":{"hostvars":{}}}'
  exit 0
fi

if ! command -v terraform >/dev/null 2>&1; then
  echo "terraform is required for hub dynamic inventory" >&2
  exit 1
fi

if ! command -v jq >/dev/null 2>&1; then
  echo "jq is required for hub dynamic inventory" >&2
  exit 1
fi

terraform_output="$(terraform -chdir="${HUB_TERRAFORM_DIR}" output -json 2>/dev/null || true)"

cluster_name="$(jq -r '.cluster_name.value // empty' <<<"${terraform_output}")"
aws_region="$(jq -r '.aws_region.value // empty' <<<"${terraform_output}")"
cluster_endpoint="$(jq -r '.cluster_endpoint.value // empty' <<<"${terraform_output}")"
update_kubeconfig_command="$(jq -r '.update_kubeconfig_command.value // empty' <<<"${terraform_output}")"
risk_normalizer_irsa_role_arn="$(jq -r '.risk_normalizer_irsa_role_arn.value // empty' <<<"${terraform_output}")"
risk_normalizer_service_account_namespace="$(jq -r '.risk_normalizer_service_account.value.namespace // empty' <<<"${terraform_output}")"
risk_normalizer_service_account_name="$(jq -r '.risk_normalizer_service_account.value.name // empty' <<<"${terraform_output}")"
prometheus_remote_write_irsa_role_arn="$(jq -r '.prometheus_remote_write_irsa_role_arn.value // empty' <<<"${terraform_output}")"
prometheus_remote_write_service_account_namespace="$(jq -r '.prometheus_remote_write_service_account.value.namespace // empty' <<<"${terraform_output}")"
prometheus_remote_write_service_account_name="$(jq -r '.prometheus_remote_write_service_account.value.name // empty' <<<"${terraform_output}")"
amp_remote_write_endpoint="$(jq -r '.amp_remote_write_endpoint.value // empty' <<<"${terraform_output}")"

if [[ -z "${cluster_name}" || -z "${aws_region}" ]]; then
  if [[ "${HUB_EKS_ALLOW_DEFAULTS:-false}" == "true" ]]; then
    cluster_name="${EKS_CLUSTER_NAME:-${AEGIS_HUB_CLUSTER_NAME}}"
    aws_region="${AWS_REGION:-${AEGIS_AWS_REGION}}"
    cluster_endpoint=""
    update_kubeconfig_command="aws eks update-kubeconfig --region ${aws_region} --name ${cluster_name}"
  else
    echo "infra/hub Terraform outputs cluster_name and aws_region are required; run infra/hub terraform apply first" >&2
    exit 1
  fi
fi

jq -n \
  --arg cluster_name "${cluster_name}" \
  --arg aws_region "${aws_region}" \
  --arg cluster_endpoint "${cluster_endpoint}" \
  --arg update_kubeconfig_command "${update_kubeconfig_command}" \
  --arg risk_normalizer_irsa_role_arn "${risk_normalizer_irsa_role_arn}" \
  --arg risk_normalizer_service_account_namespace "${risk_normalizer_service_account_namespace}" \
  --arg risk_normalizer_service_account_name "${risk_normalizer_service_account_name}" \
  --arg prometheus_remote_write_irsa_role_arn "${prometheus_remote_write_irsa_role_arn}" \
  --arg prometheus_remote_write_service_account_namespace "${prometheus_remote_write_service_account_namespace}" \
  --arg prometheus_remote_write_service_account_name "${prometheus_remote_write_service_account_name}" \
  --arg amp_remote_write_endpoint "${amp_remote_write_endpoint}" \
  '{
    hub_eks: {
      hosts: ["localhost"],
      vars: {
        ansible_connection: "local",
        eks_cluster_name: $cluster_name,
        aws_region: $aws_region,
        eks_cluster_endpoint: $cluster_endpoint,
        update_kubeconfig_command: $update_kubeconfig_command,
        risk_normalizer_irsa_role_arn: $risk_normalizer_irsa_role_arn,
        risk_normalizer_service_account_namespace: $risk_normalizer_service_account_namespace,
        risk_normalizer_service_account_name: $risk_normalizer_service_account_name,
        prometheus_remote_write_irsa_role_arn: $prometheus_remote_write_irsa_role_arn,
        prometheus_remote_write_service_account_namespace: $prometheus_remote_write_service_account_namespace,
        prometheus_remote_write_service_account_name: $prometheus_remote_write_service_account_name,
        amp_remote_write_endpoint: $amp_remote_write_endpoint
      }
    },
    _meta: {
      hostvars: {
        localhost: {
          ansible_connection: "local"
        }
      }
    }
  }'
