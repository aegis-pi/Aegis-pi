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
aegis_ensure_aws_mfa "${OTP}"

FACTORY_ID="${FACTORY_ID:-${AEGIS_FACTORY_ID}}"
AWS_REGION="${AWS_REGION:-${AEGIS_AWS_REGION}}"
THING_NAME="${THING_NAME:-${AEGIS_IOT_THING_NAME_PREFIX}-${FACTORY_ID}}"
POLICY_NAME="${POLICY_NAME:-${AEGIS_IOT_POLICY_NAME_PREFIX}-${FACTORY_ID}}"
SECRET_DIR="${SECRET_DIR:-${REPO_ROOT}/secret/iot/${FACTORY_ID}}"
REMOTE_USER="${REMOTE_USER:-${AEGIS_FACTORY_A_SSH_USER}}"
REMOTE_HOST="${REMOTE_HOST:-${AEGIS_FACTORY_A_MASTER_HOST}}"
K8S_NAMESPACE="${K8S_NAMESPACE:-${AEGIS_K8S_IOT_NAMESPACE}}"
K8S_SECRET_NAME="${K8S_SECRET_NAME:-${AEGIS_K8S_IOT_SECRET_PREFIX}-${FACTORY_ID}${AEGIS_K8S_IOT_SECRET_SUFFIX}}"
TERRAFORM_ROOT="${REPO_ROOT}/infra/hub"
export AWS_REGION
export AWS_DEFAULT_REGION="${AWS_DEFAULT_REGION:-${AWS_REGION}}"
export FACTORY_ID

require_command() {
  local command_name="$1"

  if ! command -v "${command_name}" >/dev/null 2>&1; then
    echo "missing required command: ${command_name}" >&2
    exit 1
  fi
}

require_file() {
  local file_path="$1"

  if [[ ! -f "${file_path}" ]]; then
    echo "missing required file: ${file_path}" >&2
    exit 1
  fi
}

require_command ansible-playbook
require_command aws
require_command jq
require_command ssh

require_file "${TERRAFORM_ROOT}/terraform.tfstate"
require_file "${SECRET_DIR}/certificate.pem.crt"
require_file "${SECRET_DIR}/private.pem.key"
require_file "${SECRET_DIR}/AmazonRootCA1.pem"
require_file "${SECRET_DIR}/endpoint.txt"
require_file "${SECRET_DIR}/certificate-arn.txt"
require_file "${SECRET_DIR}/certificate-id.txt"

CERTIFICATE_ARN="$(<"${SECRET_DIR}/certificate-arn.txt")"
CERTIFICATE_ID="$(<"${SECRET_DIR}/certificate-id.txt")"

echo "Verifying Hub Kubernetes platform."
cd "${REPO_ROOT}/scripts/ansible"
ansible-playbook -i inventory/hub_eks_dynamic.sh playbooks/hub_argocd_verify.yml
ansible-playbook -i inventory/hub_eks_dynamic.sh playbooks/hub_prometheus_agent_verify.yml
ansible-playbook -i inventory/hub_eks_dynamic.sh playbooks/hub_grafana_verify.yml
ansible-playbook -i inventory/hub_eks_dynamic.sh playbooks/hub_aws_load_balancer_controller_verify.yml
ansible-playbook -i inventory/hub_eks_dynamic.sh playbooks/hub_admin_ingress_verify.yml
ansible-playbook -i inventory/hub_eks_dynamic.sh playbooks/hub_tailscale_verify.yml
ansible-playbook -i inventory/hub_eks_dynamic.sh playbooks/hub_aegis_spoke_applicationset_verify.yml

echo "Verifying AWS IoT resources for ${FACTORY_ID}."
aws iot describe-thing --thing-name "${THING_NAME}" >/dev/null
aws iot get-policy --policy-name "${POLICY_NAME}" >/dev/null

certificate_status="$(
  aws iot describe-certificate \
    --certificate-id "${CERTIFICATE_ID}" \
    --query certificateDescription.status \
    --output text
)"
if [[ "${certificate_status}" != "ACTIVE" ]]; then
  echo "IoT certificate ${CERTIFICATE_ID} is ${certificate_status}, expected ACTIVE." >&2
  exit 1
fi

thing_principal_count="$(
  aws iot list-thing-principals \
    --thing-name "${THING_NAME}" \
    --query "length(principals[?@=='${CERTIFICATE_ARN}'])" \
    --output text
)"
if [[ "${thing_principal_count}" != "1" ]]; then
  echo "IoT certificate is not attached to thing ${THING_NAME}." >&2
  exit 1
fi

policy_attachment_count="$(
  aws iot list-attached-policies \
    --target "${CERTIFICATE_ARN}" \
    --query "length(policies[?policyName=='${POLICY_NAME}'])" \
    --output text
)"
if [[ "${policy_attachment_count}" != "1" ]]; then
  echo "IoT policy ${POLICY_NAME} is not attached to certificate ${CERTIFICATE_ID}." >&2
  exit 1
fi

echo "Verifying factory K3s Secret and spoke workloads on ${REMOTE_USER}@${REMOTE_HOST}."
ssh "${REMOTE_USER}@${REMOTE_HOST}" "
set -euo pipefail
kubectl -n '${K8S_NAMESPACE}' get secret '${K8S_SECRET_NAME}' >/dev/null
secret_data=\"\$(kubectl -n '${K8S_NAMESPACE}' get secret '${K8S_SECRET_NAME}' -o jsonpath='{.data}')\"
for key in certificate.pem.crt private.pem.key AmazonRootCA1.pem endpoint.txt; do
  if ! grep -q \"\${key}\" <<<\"\${secret_data}\"; then
    echo \"missing key \${key} in ${K8S_NAMESPACE}/${K8S_SECRET_NAME}\" >&2
    exit 1
  fi
done
kubectl -n '${K8S_NAMESPACE}' rollout status deployment/aegis-spoke-edge-iot-publisher --timeout=180s
kubectl -n '${K8S_NAMESPACE}' rollout status deployment/aegis-spoke-factory-a-log-adapter --timeout=180s
kubectl -n '${K8S_NAMESPACE}' get pods -l app.kubernetes.io/instance=aegis-spoke
"

echo
echo "Complete verification passed."
echo "Factory: ${FACTORY_ID}"
echo "Thing: ${THING_NAME}"
echo "Policy: ${POLICY_NAME}"
echo "K3s Secret: ${K8S_NAMESPACE}/${K8S_SECRET_NAME}"
