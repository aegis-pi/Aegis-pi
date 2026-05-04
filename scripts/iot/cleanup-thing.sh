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

# shellcheck disable=SC1091
source "${REPO_ROOT}/scripts/lib/aws-mfa.sh"
AWS_REGION="${AWS_REGION}" aegis_ensure_aws_mfa "${OTP}"
export AWS_REGION
export AWS_DEFAULT_REGION="${AWS_DEFAULT_REGION:-${AWS_REGION}}"

if [[ ! -f "${SECRET_DIR}/certificate-arn.txt" || ! -f "${SECRET_DIR}/certificate-id.txt" ]]; then
  echo "certificate ARN/ID files not found in ${SECRET_DIR}" >&2
  echo "Nothing to clean up from local metadata." >&2
  exit 1
fi

CERTIFICATE_ARN="$(cat "${SECRET_DIR}/certificate-arn.txt")"
CERTIFICATE_ID="$(cat "${SECRET_DIR}/certificate-id.txt")"

aws iot detach-thing-principal \
  --thing-name "${THING_NAME}" \
  --principal "${CERTIFICATE_ARN}" \
  >/dev/null 2>&1 || true

aws iot detach-policy \
  --policy-name "${POLICY_NAME}" \
  --target "${CERTIFICATE_ARN}" \
  >/dev/null 2>&1 || true

aws iot update-certificate \
  --certificate-id "${CERTIFICATE_ID}" \
  --new-status INACTIVE \
  >/dev/null 2>&1 || true

aws iot delete-certificate \
  --certificate-id "${CERTIFICATE_ID}" \
  >/dev/null 2>&1 || true

aws iot delete-policy \
  --policy-name "${POLICY_NAME}" \
  >/dev/null 2>&1 || true

aws iot delete-thing \
  --thing-name "${THING_NAME}" \
  >/dev/null 2>&1 || true

if [[ "${DELETE_LOCAL_FILES}" == "true" ]]; then
  find "${SECRET_DIR}" -mindepth 1 -maxdepth 1 -type f -delete
  echo "Deleted local files in ${SECRET_DIR}"
else
  echo "Kept local files in ${SECRET_DIR}"
fi

echo "Cleaned up IoT Thing resources for ${THING_NAME}"
