#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

AWS_REGION="${AWS_REGION:-ap-south-1}"
FACTORY_ID="${FACTORY_ID:-factory-a}"
THING_NAME="${THING_NAME:-AEGIS-IoTThing-${FACTORY_ID}}"
POLICY_NAME="${POLICY_NAME:-AEGIS-IoTPolicy-${FACTORY_ID}}"
TOPIC_PREFIX="${TOPIC_PREFIX:-aegis/${FACTORY_ID}}"
SECRET_DIR="${SECRET_DIR:-${REPO_ROOT}/secret/iot/${FACTORY_ID}}"

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "missing required command: $1" >&2
    exit 1
  fi
}

require_command aws
require_command jq
require_command curl

mkdir -p "${SECRET_DIR}"
chmod 700 "${REPO_ROOT}/secret" "${REPO_ROOT}/secret/iot" "${SECRET_DIR}"

ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"

if aws iot describe-thing --thing-name "${THING_NAME}" >/dev/null 2>&1; then
  echo "IoT Thing already exists: ${THING_NAME}"
else
  aws iot create-thing \
    --thing-name "${THING_NAME}" \
    --attribute-payload "attributes={factory_id=${FACTORY_ID},project=AEGIS}" \
    >/dev/null
  echo "Created IoT Thing: ${THING_NAME}"
fi

cat >"${SECRET_DIR}/iot-policy.json" <<JSON
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["iot:Connect"],
      "Resource": ["arn:aws:iot:${AWS_REGION}:${ACCOUNT_ID}:client/${THING_NAME}"]
    },
    {
      "Effect": "Allow",
      "Action": ["iot:Publish"],
      "Resource": ["arn:aws:iot:${AWS_REGION}:${ACCOUNT_ID}:topic/${TOPIC_PREFIX}/*"]
    },
    {
      "Effect": "Allow",
      "Action": ["iot:Subscribe"],
      "Resource": ["arn:aws:iot:${AWS_REGION}:${ACCOUNT_ID}:topicfilter/${TOPIC_PREFIX}/*"]
    },
    {
      "Effect": "Allow",
      "Action": ["iot:Receive"],
      "Resource": ["arn:aws:iot:${AWS_REGION}:${ACCOUNT_ID}:topic/${TOPIC_PREFIX}/*"]
    }
  ]
}
JSON

if aws iot get-policy --policy-name "${POLICY_NAME}" >/dev/null 2>&1; then
  echo "IoT Policy already exists: ${POLICY_NAME}"
else
  aws iot create-policy \
    --policy-name "${POLICY_NAME}" \
    --policy-document "file://${SECRET_DIR}/iot-policy.json" \
    >/dev/null
  echo "Created IoT Policy: ${POLICY_NAME}"
fi

if [[ -f "${SECRET_DIR}/certificate-arn.txt" || -f "${SECRET_DIR}/private.pem.key" ]]; then
  echo "certificate files already exist in ${SECRET_DIR}" >&2
  echo "Refusing to overwrite existing certificate material. Use cleanup-thing.sh or move the directory first." >&2
  exit 1
fi

aws iot create-keys-and-certificate \
  --set-as-active \
  --certificate-pem-outfile "${SECRET_DIR}/certificate.pem.crt" \
  --public-key-outfile "${SECRET_DIR}/public.pem.key" \
  --private-key-outfile "${SECRET_DIR}/private.pem.key" \
  >"${SECRET_DIR}/certificate.json"

jq -r '.certificateArn' "${SECRET_DIR}/certificate.json" >"${SECRET_DIR}/certificate-arn.txt"
jq -r '.certificateId' "${SECRET_DIR}/certificate.json" >"${SECRET_DIR}/certificate-id.txt"

CERTIFICATE_ARN="$(cat "${SECRET_DIR}/certificate-arn.txt")"

aws iot attach-policy \
  --policy-name "${POLICY_NAME}" \
  --target "${CERTIFICATE_ARN}"

aws iot attach-thing-principal \
  --thing-name "${THING_NAME}" \
  --principal "${CERTIFICATE_ARN}"

curl -fsSL \
  https://www.amazontrust.com/repository/AmazonRootCA1.pem \
  -o "${SECRET_DIR}/AmazonRootCA1.pem"

aws iot describe-endpoint \
  --endpoint-type iot:Data-ATS \
  --query endpointAddress \
  --output text \
  >"${SECRET_DIR}/endpoint.txt"

cat >"${SECRET_DIR}/registration-summary.txt" <<SUMMARY
AWS_REGION=${AWS_REGION}
ACCOUNT_ID=${ACCOUNT_ID}
FACTORY_ID=${FACTORY_ID}
THING_NAME=${THING_NAME}
POLICY_NAME=${POLICY_NAME}
TOPIC_PREFIX=${TOPIC_PREFIX}
CERTIFICATE_ARN=${CERTIFICATE_ARN}
SECRET_DIR=${SECRET_DIR}
SUMMARY

chmod 600 "${SECRET_DIR}"/*
chmod 700 "${SECRET_DIR}"

echo "Registered IoT Thing and certificate."
echo "Secret material directory: ${SECRET_DIR}"
echo "Thing: ${THING_NAME}"
echo "Policy: ${POLICY_NAME}"
echo "Topic prefix: ${TOPIC_PREFIX}"
