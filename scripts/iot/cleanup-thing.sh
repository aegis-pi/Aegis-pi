#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# shellcheck disable=SC1091
source "${REPO_ROOT}/scripts/lib/config.sh"
aegis_load_config "${REPO_ROOT}"

AWS_REGION="${AWS_REGION:-${AEGIS_AWS_REGION}}"
FACTORY_ID="${FACTORY_ID:-${AEGIS_FACTORY_ID}}"
SECRET_DIR="${SECRET_DIR:-${REPO_ROOT}/secret/iot/${FACTORY_ID}}"
DELETE_LOCAL_FILES="${DELETE_LOCAL_FILES:-false}"
OTP="${1:-}"

SUMMARY_FILE="${SECRET_DIR}/registration-summary.txt"
if [[ -f "${SUMMARY_FILE}" ]]; then
  SUMMARY_THING_NAME="$(awk -F= '$1 == "THING_NAME" { print $2 }' "${SUMMARY_FILE}")"
  SUMMARY_POLICY_NAME="$(awk -F= '$1 == "POLICY_NAME" { print $2 }' "${SUMMARY_FILE}")"
fi

THING_NAME="${THING_NAME:-${SUMMARY_THING_NAME:-${AEGIS_IOT_THING_NAME_PREFIX}-${FACTORY_ID}}}"
POLICY_NAME="${POLICY_NAME:-${SUMMARY_POLICY_NAME:-${AEGIS_IOT_POLICY_NAME_PREFIX}-${FACTORY_ID}}}"

thing_exists_in_aws() {
  aws iot describe-thing \
    --thing-name "${THING_NAME}" \
    >/dev/null 2>&1
}

append_certificate_arn() {
  local certificate_arn="$1"
  local existing

  [[ -n "${certificate_arn}" && "${certificate_arn}" != "None" ]] || return 0

  for existing in "${CERTIFICATE_ARNS[@]:-}"; do
    if [[ "${existing}" == "${certificate_arn}" ]]; then
      return 0
    fi
  done

  CERTIFICATE_ARNS+=("${certificate_arn}")
}

# shellcheck disable=SC1091
source "${REPO_ROOT}/scripts/lib/aws-mfa.sh"
AWS_REGION="${AWS_REGION}" aegis_ensure_aws_mfa "${OTP}"
export AWS_REGION
export AWS_DEFAULT_REGION="${AWS_DEFAULT_REGION:-${AWS_REGION}}"

CERTIFICATE_ARNS=()

if [[ -f "${SECRET_DIR}/certificate-arn.txt" ]]; then
  append_certificate_arn "$(cat "${SECRET_DIR}/certificate-arn.txt")"
fi

if [[ -f "${SECRET_DIR}/certificate-id.txt" ]]; then
  LOCAL_CERTIFICATE_ID="$(cat "${SECRET_DIR}/certificate-id.txt")"
  LOCAL_CERTIFICATE_ARN="$(
    aws iot describe-certificate \
      --certificate-id "${LOCAL_CERTIFICATE_ID}" \
      --query certificateDescription.certificateArn \
      --output text \
      2>/dev/null || true
  )"
  append_certificate_arn "${LOCAL_CERTIFICATE_ARN}"
fi

if thing_exists_in_aws; then
  while IFS= read -r thing_principal; do
    append_certificate_arn "${thing_principal}"
  done < <(
    aws iot list-thing-principals \
      --thing-name "${THING_NAME}" \
      --query principals \
      --output text \
      2>/dev/null | tr '\t' '\n' || true
  )
else
  echo "IoT Thing not found: ${THING_NAME}"
fi

while IFS= read -r policy_target; do
  append_certificate_arn "${policy_target}"
done < <(
  aws iot list-targets-for-policy \
    --policy-name "${POLICY_NAME}" \
    --query targets \
    --output text \
    2>/dev/null | tr '\t' '\n' || true
)

if [[ "${#CERTIFICATE_ARNS[@]}" -eq 0 ]]; then
  echo "No IoT certificate principals found for ${THING_NAME}."
fi

for certificate_arn in "${CERTIFICATE_ARNS[@]}"; do
  certificate_id="${certificate_arn##*/}"

  aws iot detach-thing-principal \
    --thing-name "${THING_NAME}" \
    --principal "${certificate_arn}" \
    >/dev/null 2>&1 || true

  while IFS= read -r attached_policy; do
    [[ -n "${attached_policy}" && "${attached_policy}" != "None" ]] || continue

    aws iot detach-policy \
      --policy-name "${attached_policy}" \
      --target "${certificate_arn}" \
      >/dev/null 2>&1 || true
  done < <(
    aws iot list-attached-policies \
      --target "${certificate_arn}" \
      --query 'policies[].policyName' \
      --output text \
      2>/dev/null | tr '\t' '\n' || true
  )

  aws iot update-certificate \
    --certificate-id "${certificate_id}" \
    --new-status INACTIVE \
    >/dev/null 2>&1 || true

  aws iot delete-certificate \
    --certificate-id "${certificate_id}" \
    >/dev/null 2>&1 || true
done

aws iot delete-policy \
  --policy-name "${POLICY_NAME}" \
  >/dev/null 2>&1 || true

aws iot delete-thing \
  --thing-name "${THING_NAME}" \
  >/dev/null 2>&1 || true

if [[ "${DELETE_LOCAL_FILES}" == "true" ]]; then
  if [[ -d "${SECRET_DIR}" ]]; then
    find "${SECRET_DIR}" -mindepth 1 -maxdepth 1 -type f -delete
    echo "Deleted local files in ${SECRET_DIR}"
  fi
else
  echo "Kept local files in ${SECRET_DIR}"
fi

echo "Cleaned up IoT Thing resources for ${THING_NAME}"
