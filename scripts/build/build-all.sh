#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
OTP=""
REQUEST_ADMIN_UI=false
ENABLE_ADMIN_UI_INGRESS=false

usage() {
  cat <<'USAGE'
Usage: scripts/build/build-all.sh [--admin-ui] [--admin-ui-ingress] [MFA_OTP]

Options:
  --admin-ui          Prepare Admin UI Route53/ACM outputs only. Ingress is enabled later.
  --admin-ui-ingress  Enable Admin UI HTTPS Ingress/ALB during the Hub build.
                      Use only after domain NS delegation and ACM ISSUED.
  -h, --help          Show this help.
USAGE
}

while [[ "$#" -gt 0 ]]; do
  case "$1" in
    --admin-ui)
      REQUEST_ADMIN_UI=true
      ;;
    --admin-ui-ingress)
      ENABLE_ADMIN_UI_INGRESS=true
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

BUILD_FOUNDATION="${BUILD_FOUNDATION:-true}"
BUILD_HUB="${BUILD_HUB:-true}"
BUILD_IOT="${BUILD_IOT:-true}"
FACTORY_ID="${FACTORY_ID:-${AEGIS_FACTORY_ID}}"
IOT_CERT_METADATA="${REPO_ROOT}/secret/iot/${FACTORY_ID}/certificate-arn.txt"

if [[ "${REQUEST_ADMIN_UI}" == "true" ]]; then
  echo "--admin-ui now prepares Admin UI Route53/ACM outputs only."
  echo "After setting the printed NS records at the registrar, run scripts/build/build-admin-ui-after-ns.sh."
fi

if [[ "${ENABLE_ADMIN_UI_INGRESS}" == "true" ]]; then
  export ADMIN_UI_INGRESS_ENABLED=true
fi

cd "${REPO_ROOT}"

if [[ "${BUILD_FOUNDATION}" == "true" || "${BUILD_HUB}" == "true" || \
  ( "${BUILD_IOT}" == "true" && ! -f "${IOT_CERT_METADATA}" ) ]]; then
  # shellcheck disable=SC1091
  source "${REPO_ROOT}/scripts/lib/aws-mfa.sh"
  aegis_ensure_aws_mfa "${OTP}"
fi

if [[ "${BUILD_FOUNDATION}" == "true" ]]; then
  scripts/build/build-foundation.sh "${OTP}"
fi

if [[ "${BUILD_HUB}" == "true" ]]; then
  scripts/build/build-hub.sh "${OTP}"
fi

if [[ "${BUILD_IOT}" == "true" ]]; then
  scripts/build/build-iot-factory-a.sh "${OTP}"
fi

echo "Build flow completed."
