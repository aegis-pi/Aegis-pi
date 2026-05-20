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
#

set -e

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

FC_MASTER_IP="${FACTORY_C_MASTER_IP:-}"
FC_WORKER_IP="${FACTORY_C_WORKER_IP:-}"
FC_USER="${FACTORY_C_USER:-}"
FC_SERVICE="${FACTORY_C_SERVICE:-aegis-factory-c-dummy-generator.service}"

require_factory_b_env() {
  if [[ -z "$FB_MASTER_IP" || -z "$FB_WORKER_IP" || -z "$FB_USER" ]]; then
    echo "Missing required factory-b env: FACTORY_B_MASTER_IP, FACTORY_B_WORKER_IP, FACTORY_B_USER" >&2
    exit 1
  fi
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
  if [ "$ACTION" = "status" ]; then
    ssh "$FB_USER@$FB_MASTER_IP" \
      "ssh $FB_USER@$FB_WORKER_IP 'systemctl status $FB_SERVICE --no-pager' || true"
  else
    ssh "$FB_USER@$FB_MASTER_IP" \
      "ssh $FB_USER@$FB_WORKER_IP 'sudo systemctl $ACTION $FB_SERVICE'"
    echo "Done."
  fi
}

manage_factory_c() {
  require_factory_c_env
  echo ">>> Factory C (factory-c-worker via master): Running '$ACTION'..."
  if [ "$ACTION" = "status" ]; then
    ssh "$FC_USER@$FC_MASTER_IP" \
      "ssh $FC_USER@$FC_WORKER_IP 'systemctl status $FC_SERVICE --no-pager' || true"
  else
    ssh "$FC_USER@$FC_MASTER_IP" \
      "ssh $FC_USER@$FC_WORKER_IP 'sudo systemctl $ACTION $FC_SERVICE'"
    echo "Done."
  fi
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
