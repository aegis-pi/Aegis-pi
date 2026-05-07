#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
OTP="${1:-}"

# shellcheck disable=SC1091
source "${REPO_ROOT}/scripts/lib/config.sh"
aegis_load_config "${REPO_ROOT}"
# shellcheck disable=SC1091
source "${REPO_ROOT}/scripts/lib/aws-mfa.sh"

WAIT_SECONDS="${ADMIN_UI_CERTIFICATE_WAIT_SECONDS:-1800}"
WAIT_INTERVAL_SECONDS="${ADMIN_UI_CERTIFICATE_WAIT_INTERVAL_SECONDS:-30}"
TERRAFORM_ROOT="${REPO_ROOT}/infra/hub"

cd "${REPO_ROOT}"
aegis_ensure_aws_mfa "${OTP}"

if [[ ! -f "${TERRAFORM_ROOT}/terraform.tfstate" ]]; then
  echo "Missing ${TERRAFORM_ROOT}/terraform.tfstate. Run scripts/build/build-all.sh first." >&2
  exit 1
fi

"${REPO_ROOT}/scripts/ops/admin-ui-nameservers.sh"

certificate_arn="$(terraform -chdir="${TERRAFORM_ROOT}" output -raw admin_ui_certificate_arn)"
domain_name="$(terraform -chdir="${TERRAFORM_ROOT}" output -raw admin_ui_domain_name)"
argocd_host="$(terraform -chdir="${TERRAFORM_ROOT}" output -raw admin_ui_argocd_host)"
grafana_host="$(terraform -chdir="${TERRAFORM_ROOT}" output -raw admin_ui_grafana_host)"

echo "Waiting for ACM certificate to become ISSUED."
echo "Domain: ${domain_name}"
echo "Certificate: ${certificate_arn}"

deadline=$((SECONDS + WAIT_SECONDS))
status=""

while (( SECONDS <= deadline )); do
  status="$(
    aws acm describe-certificate \
      --region "${AEGIS_AWS_REGION}" \
      --certificate-arn "${certificate_arn}" \
      --query 'Certificate.Status' \
      --output text
  )"

  echo "ACM status: ${status}"

  if [[ "${status}" == "ISSUED" ]]; then
    break
  fi

  if [[ "${status}" == "FAILED" ]]; then
    echo "ACM certificate validation failed. Check Route53/Gabia DNS delegation." >&2
    exit 1
  fi

  sleep "${WAIT_INTERVAL_SECONDS}"
done

if [[ "${status}" != "ISSUED" ]]; then
  echo "ACM certificate is still ${status:-unknown} after ${WAIT_SECONDS}s." >&2
  echo "Confirm that Gabia NS delegation matches secret/admin-ui-nameservers.txt, then rerun this script." >&2
  exit 1
fi

export ADMIN_UI_INGRESS_ENABLED=true

cd "${REPO_ROOT}/scripts/ansible"
ansible-playbook -i inventory/hub_eks_dynamic.sh playbooks/hub_admin_ingress_bootstrap.yml
ansible-playbook -i inventory/hub_eks_dynamic.sh playbooks/hub_admin_ingress_verify.yml

echo
echo "Admin UI HTTPS endpoints are ready:"
echo "  https://${argocd_host}"
echo "  https://${grafana_host}"
