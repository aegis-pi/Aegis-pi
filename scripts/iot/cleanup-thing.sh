#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

AWS_REGION="${AWS_REGION:-ap-south-1}"
FACTORY_ID="${FACTORY_ID:-factory-a}"
THING_NAME="${THING_NAME:-AEGIS-IoTThing-${FACTORY_ID}}"
POLICY_NAME="${POLICY_NAME:-AEGIS-IoTPolicy-${FACTORY_ID}}"
SECRET_DIR="${SECRET_DIR:-${REPO_ROOT}/secret/iot/${FACTORY_ID}}"
DELETE_LOCAL_FILES="${DELETE_LOCAL_FILES:-false}"

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
