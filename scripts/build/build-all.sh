#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
OTP=""
BUILD_ADMIN_UI_AFTER_NS="${BUILD_ADMIN_UI_AFTER_NS:-false}"

usage() {
  cat <<'USAGE'
Usage: scripts/build/build-all.sh [--foundation] [--data-pipe] [--admin-ui-after-ns] [--iot] [MFA_OTP]

Options:
  --foundation         Include foundation Terraform apply.
  --data-pipe          Apply infra/data-pipeline (IoT Rules factory-a/b/c, Lambda).
                       Requires foundation to be deployed first (DynamoDB and S3 live there).
                       Safe to re-run against an existing data-pipeline deployment.
  --admin-ui-after-ns  Enable Admin UI HTTPS Ingress/ALB after Gabia NS delegation.
  --iot                Include factory-a IoT Thing/certificate and K3s Secret registration.
  --admin-ui           Deprecated no-op; Foundation owns Route53/ACM and Hub reuses those outputs.
  --admin-ui-ingress   Deprecated alias for --admin-ui-after-ns.
  -h, --help           Show this help.
USAGE
}

while [[ "$#" -gt 0 ]]; do
  case "$1" in
    --foundation)
      BUILD_FOUNDATION=true
      ;;
    --data-pipe)
      BUILD_DATA_PIPE=true
      ;;
    --admin-ui)
      echo "--admin-ui is now a no-op. Foundation owns Route53/ACM and Hub reuses those outputs."
      ;;
    --admin-ui-ingress)
      echo "--admin-ui-ingress is deprecated; using --admin-ui-after-ns."
      BUILD_ADMIN_UI_AFTER_NS=true
      ;;
    --admin-ui-after-ns)
      BUILD_ADMIN_UI_AFTER_NS=true
      ;;
    --iot)
      BUILD_IOT=true
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

BUILD_FOUNDATION="${BUILD_FOUNDATION:-false}"
BUILD_DATA_PIPE="${BUILD_DATA_PIPE:-false}"
BUILD_HUB="${BUILD_HUB:-true}"
BUILD_IOT="${BUILD_IOT:-false}"
AEGIS_BUILD_PREFLIGHT="${AEGIS_BUILD_PREFLIGHT:-true}"
FACTORY_ID="${FACTORY_ID:-${AEGIS_FACTORY_ID}}"
IOT_CERT_METADATA="${REPO_ROOT}/secret/iot/${FACTORY_ID}/certificate-arn.txt"

export BUILD_FOUNDATION BUILD_DATA_PIPE BUILD_HUB BUILD_ADMIN_UI_AFTER_NS BUILD_IOT

cd "${REPO_ROOT}"

if [[ "${BUILD_FOUNDATION}" == "true" || "${BUILD_DATA_PIPE}" == "true" || \
  "${BUILD_HUB}" == "true" || "${BUILD_ADMIN_UI_AFTER_NS}" == "true" || \
  ( "${BUILD_IOT}" == "true" && ! -f "${IOT_CERT_METADATA}" ) ]]; then
  # shellcheck disable=SC1091
  source "${REPO_ROOT}/scripts/lib/aws-mfa.sh"
  aegis_ensure_aws_mfa "${OTP}"
fi

if [[ "${BUILD_FOUNDATION}" == "true" ]]; then
  scripts/build/build-foundation.sh "${OTP}"
  BUILD_FOUNDATION=false
  export BUILD_FOUNDATION
fi

if [[ "${AEGIS_BUILD_PREFLIGHT}" == "true" ]]; then
  scripts/build/preflight.sh
fi

if [[ "${BUILD_HUB}" == "true" ]]; then
  scripts/build/build-hub.sh "${OTP}"
fi

if [[ "${BUILD_DATA_PIPE}" == "true" ]]; then
  scripts/build/build-data-pipe.sh "${OTP}"
  BUILD_DATA_PIPE=false
  export BUILD_DATA_PIPE
fi

if [[ "${BUILD_ADMIN_UI_AFTER_NS}" == "true" ]]; then
  scripts/build/build-admin-ui-after-ns.sh "${OTP}"
fi

if [[ "${BUILD_IOT}" == "true" ]]; then
  scripts/build/build-iot-factory-a.sh "${OTP}"
fi

echo "Build flow completed."
