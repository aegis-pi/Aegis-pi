#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
OTP=""
PLAN_ONLY=false

usage() {
  cat <<'USAGE'
Usage: scripts/build/reconcile-data-pipe-eks-access.sh [--plan-only] [MFA_OTP]

Re-apply only the data-pipeline Terraform resources that bind
CloudInfraSlowCollector to the current Hub EKS cluster.

Use this after destroying and recreating Hub while keeping data-pipeline alive.
USAGE
}

while [[ "$#" -gt 0 ]]; do
  case "$1" in
    --plan-only)
      PLAN_ONLY=true
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    --)
      shift
      if [[ "$#" -gt 0 ]]; then
        OTP="$1"
        shift
      fi
      break
      ;;
    -*)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 1
      ;;
    *)
      if [[ -n "${OTP}" ]]; then
        echo "Unexpected extra argument: $1" >&2
        usage >&2
        exit 1
      fi
      OTP="$1"
      ;;
  esac
  shift
done

# shellcheck disable=SC1091
source "${REPO_ROOT}/scripts/lib/config.sh"
aegis_load_config "${REPO_ROOT}"
# shellcheck disable=SC1091
source "${REPO_ROOT}/scripts/lib/aws-mfa.sh"
aegis_ensure_aws_mfa "${OTP}"
# shellcheck disable=SC1091
source "${REPO_ROOT}/scripts/lib/terraform.sh"

export AWS_RETRY_MODE="${AWS_RETRY_MODE:-adaptive}"
export AWS_MAX_ATTEMPTS="${AWS_MAX_ATTEMPTS:-10}"

HUB_ROOT="${REPO_ROOT}/infra/hub"
DATA_PIPE_ROOT="${REPO_ROOT}/infra/data-pipeline"

aegis_terraform_require_state_resources "${HUB_ROOT}" "hub"
aegis_terraform_require_state_resources "${DATA_PIPE_ROOT}" "data-pipeline"

HUB_CLUSTER_NAME="$(terraform -chdir="${REPO_ROOT}/infra/hub" output -raw cluster_name)"

echo "Checking Hub EKS cluster ${HUB_CLUSTER_NAME} in ${AEGIS_AWS_REGION}..."
aws eks wait cluster-active \
  --region "${AEGIS_AWS_REGION}" \
  --name "${HUB_CLUSTER_NAME}"

ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
SLOW_COLLECTOR_ROLE_ARN="arn:aws:iam::${ACCOUNT_ID}:role/AEGIS-IAMRole-Lambda-CloudInfraSlowCollector"

cd "${REPO_ROOT}/infra/data-pipeline"

if [[ ! -f terraform.tfvars && -f terraform.tfvars.example ]]; then
  cp terraform.tfvars.example terraform.tfvars
fi

terraform init
terraform validate
terraform plan \
  -out=tfplan.eks-access \
  -target=aws_eks_access_entry.cloud_infra_slow_collector \
  -target=aws_eks_access_policy_association.cloud_infra_slow_collector_view

if [[ "${PLAN_ONLY}" == "true" ]]; then
  echo "Plan only mode enabled. Review tfplan.eks-access, then rerun without --plan-only to apply."
  exit 0
fi

terraform apply tfplan.eks-access

echo "Verifying EKS access entry..."
aws eks describe-access-entry \
  --region "${AEGIS_AWS_REGION}" \
  --cluster-name "${HUB_CLUSTER_NAME}" \
  --principal-arn "${SLOW_COLLECTOR_ROLE_ARN}" \
  --query 'accessEntry.{principalArn:principalArn,type:type,createdAt:createdAt,modifiedAt:modifiedAt}' \
  --output table

echo "Verifying EKS access policy association..."
aws eks list-associated-access-policies \
  --region "${AEGIS_AWS_REGION}" \
  --cluster-name "${HUB_CLUSTER_NAME}" \
  --principal-arn "${SLOW_COLLECTOR_ROLE_ARN}" \
  --query 'associatedAccessPolicies[*].{policyArn:policyArn,scope:accessScope.type}' \
  --output table

echo "CloudInfraSlowCollector EKS access reconcile completed."
