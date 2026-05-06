#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# shellcheck disable=SC1091
source "${REPO_ROOT}/scripts/lib/config.sh"
aegis_load_config "${REPO_ROOT}"

AWS_REGION="${AWS_REGION:-${AEGIS_AWS_REGION}}"
FACTORY_ID="${FACTORY_ID:-${AEGIS_FACTORY_ID}}"
SOURCE_TYPE="${SOURCE_TYPE:-sensor}"
TOPIC="${TOPIC:-${AEGIS_IOT_TOPIC_ROOT}/${FACTORY_ID}/${SOURCE_TYPE}}"
OTP="${1:-}"

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "missing required command: $1" >&2
    exit 1
  fi
}

require_command aws
require_command jq

# shellcheck disable=SC1091
source "${REPO_ROOT}/scripts/lib/aws-mfa.sh"
AWS_REGION="${AWS_REGION}" aegis_ensure_aws_mfa "${OTP}"
export AWS_REGION
export AWS_DEFAULT_REGION="${AWS_DEFAULT_REGION:-${AWS_REGION}}"

ENDPOINT="$(
  aws iot describe-endpoint \
    --endpoint-type iot:Data-ATS \
    --query endpointAddress \
    --output text
)"

MESSAGE_ID="${MESSAGE_ID:-manual-$(date -u +%Y%m%dT%H%M%SZ)-${RANDOM}}"
SOURCE_TIMESTAMP="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
PAYLOAD_FILE="$(mktemp)"

cleanup() {
  rm -f "${PAYLOAD_FILE}"
}
trap cleanup EXIT

jq -n \
  --arg message_id "${MESSAGE_ID}" \
  --arg factory_id "${FACTORY_ID}" \
  --arg source_type "${SOURCE_TYPE}" \
  --arg source_timestamp "${SOURCE_TIMESTAMP}" \
  '{
    message_id: $message_id,
    factory_id: $factory_id,
    node_id: "manual-test",
    source_type: $source_type,
    measurement: "manual_publish_test",
    source_timestamp: $source_timestamp,
    published_at: $source_timestamp,
    payload: {
      temperature_c: 25.2,
      humidity_pct: 43.1,
      status: "ok"
    }
  }' >"${PAYLOAD_FILE}"

aws iot-data publish \
  --endpoint-url "https://${ENDPOINT}" \
  --topic "${TOPIC}" \
  --qos 1 \
  --payload "fileb://${PAYLOAD_FILE}" \
  --cli-binary-format raw-in-base64-out

echo "Published IoT test message."
echo "Topic: ${TOPIC}"
echo "Message ID: ${MESSAGE_ID}"
echo "Expected S3 prefix: s3://aegis-bucket-data/raw/${FACTORY_ID}/${SOURCE_TYPE}/"
