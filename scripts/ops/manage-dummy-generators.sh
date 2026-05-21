#!/usr/bin/env bash
#
# Manage VM Spoke Dummy Generators (Factory B / C)
# Usage: ./manage-dummy-generators.sh [start|stop|status] [factory-b|factory-c]
#
# Required environment variables:
#   FACTORY_B_MASTER_IP, FACTORY_B_WORKER_IP, FACTORY_B_USER
#   FACTORY_C_MASTER_IP, FACTORY_C_WORKER_IP, FACTORY_C_USER
#
# Optional:
#   FACTORY_B_SERVICE, FACTORY_C_SERVICE
#   AEGIS_DUMMY_GENERATORS_ENV
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${AEGIS_DUMMY_GENERATORS_ENV:-${SCRIPT_DIR}/dummy-generators.env}"

if [[ -f "${ENV_FILE}" ]]; then
  # shellcheck disable=SC1090
  source "${ENV_FILE}"
fi

ACTION="$1"
TARGET_FACTORY="$2"

if [[ -z "$ACTION" || ! "$ACTION" =~ ^(start|stop|status)$ ]]; then
  echo "Usage: $0 [start|stop|status] [factory-b|factory-c]"
  exit 1
fi

FB_MASTER_IP="${FACTORY_B_MASTER_IP:-}"
FB_WORKER_IP="${FACTORY_B_WORKER_IP:-}"
FB_USER="${FACTORY_B_USER:-}"
FB_SERVICE="${FACTORY_B_SERVICE:-aegis-factory-b-dummy-generator.service}"
FB_LEGACY_PUBLISHER_SERVICE="${FACTORY_B_LEGACY_PUBLISHER_SERVICE:-aegis-factory-b-dummy-publisher.service}"

FC_MASTER_IP="${FACTORY_C_MASTER_IP:-}"
FC_WORKER_IP="${FACTORY_C_WORKER_IP:-}"
FC_USER="${FACTORY_C_USER:-}"
FC_SERVICE="${FACTORY_C_SERVICE:-aegis-factory-c-dummy-generator.service}"
FC_LEGACY_PUBLISHER_SERVICE="${FACTORY_C_LEGACY_PUBLISHER_SERVICE:-aegis-factory-c-dummy-publisher.service}"

require_factory_b_env() {
  if [[ -z "$FB_MASTER_IP" || -z "$FB_WORKER_IP" || -z "$FB_USER" ]]; then
    echo "Missing required factory-b env: FACTORY_B_MASTER_IP, FACTORY_B_WORKER_IP, FACTORY_B_USER" >&2
    exit 1
  fi
}

run_on_worker() {
  local user="$1"
  local master_ip="$2"
  local worker_ip="$3"
  local generator_service="$4"
  local legacy_publisher_service="$5"
  local remote_command

  case "${ACTION}" in
    status)
      printf -v remote_command \
        "systemctl status %q --no-pager || true" \
        "${generator_service}"
      ;;
    stop)
      printf -v remote_command \
        'if systemctl list-unit-files %q --no-legend --no-pager | grep -q .; then sudo systemctl stop %q; fi; sudo systemctl stop %q; sleep 1; STATUS=$(systemctl is-active %q); echo "[verify] %q: ${STATUS}"; [ "${STATUS}" = inactive ] || [ "${STATUS}" = failed ] || { echo "ERROR: %q did not stop (status: ${STATUS})" >&2; exit 1; }' \
        "${legacy_publisher_service}" \
        "${legacy_publisher_service}" \
        "${generator_service}" \
        "${generator_service}" \
        "${generator_service}" \
        "${generator_service}"
      ;;
    start)
      printf -v remote_command \
        'sudo systemctl start %q; sleep 1; STATUS=$(systemctl is-active %q); echo "[verify] %q: ${STATUS}"; [ "${STATUS}" = active ] || { echo "ERROR: %q did not start (status: ${STATUS})" >&2; exit 1; }' \
        "${generator_service}" \
        "${generator_service}" \
        "${generator_service}" \
        "${generator_service}"
      ;;
  esac

  ssh -tt -J "${user}@${master_ip}" "${user}@${worker_ip}" "${remote_command}"
}

require_factory_c_env() {
  if [[ -z "$FC_MASTER_IP" || -z "$FC_WORKER_IP" || -z "$FC_USER" ]]; then
    echo "Missing required factory-c env: FACTORY_C_MASTER_IP, FACTORY_C_WORKER_IP, FACTORY_C_USER" >&2
    exit 1
  fi
}

manage_factory_b() {
  require_factory_b_env
  echo ">>> Factory B (worker1 via master): Running '$ACTION'..."
  echo "    Password prompts may appear for master SSH, worker SSH, and worker sudo."
  run_on_worker "${FB_USER}" "${FB_MASTER_IP}" "${FB_WORKER_IP}" "${FB_SERVICE}" "${FB_LEGACY_PUBLISHER_SERVICE}"
  echo "Done."
}

manage_factory_c() {
  require_factory_c_env
  echo ">>> Factory C (factory-c-worker via master): Running '$ACTION'..."
  echo "    Password prompts may appear for master SSH, worker SSH, and worker sudo."
  run_on_worker "${FC_USER}" "${FC_MASTER_IP}" "${FC_WORKER_IP}" "${FC_SERVICE}" "${FC_LEGACY_PUBLISHER_SERVICE}"
  echo "Done."
}

if [ -z "$TARGET_FACTORY" ]; then
  manage_factory_b
  echo ""
  manage_factory_c
elif [ "$TARGET_FACTORY" = "factory-b" ]; then
  manage_factory_b
elif [ "$TARGET_FACTORY" = "factory-c" ]; then
  manage_factory_c
else
  echo "Unknown factory: $TARGET_FACTORY"
  echo "Supported factories: factory-b, factory-c"
  exit 1
fi
