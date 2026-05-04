#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
OTP="${1:-}"

BUILD_FOUNDATION="${BUILD_FOUNDATION:-true}"
BUILD_HUB="${BUILD_HUB:-true}"
BUILD_IOT="${BUILD_IOT:-true}"

cd "${REPO_ROOT}"

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
