#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
TARGET_FACTORY="${1:-}"

if [[ -n "${TARGET_FACTORY}" && "${TARGET_FACTORY}" != "factory-b" && "${TARGET_FACTORY}" != "factory-c" ]]; then
  echo "Usage: $0 [factory-b|factory-c]" >&2
  exit 1
fi

"${REPO_ROOT}/scripts/ops/manage-dummy-generators.sh" stop "${TARGET_FACTORY}"
