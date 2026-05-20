#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FACTORY_TARGET=factory-c "${SCRIPT_DIR}/lib/connect-spoke.sh" "$@"
