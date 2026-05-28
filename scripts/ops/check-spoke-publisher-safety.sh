#!/usr/bin/env bash
set -euo pipefail

FACTORIES=("$@")
if [[ "${#FACTORIES[@]}" -eq 0 ]]; then
  FACTORIES=(factory-a factory-b factory-c)
fi

NAMESPACE="${SPOKE_NAMESPACE:-ai-apps}"
EXIT_CODE=0

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "missing required command: $1" >&2
    exit 1
  fi
}

kubeconfig_for_factory() {
  case "$1" in
    factory-a)
      echo "${AEGIS_FACTORY_A_DIRECT_KUBECONFIG:-${HOME}/Aegis/.aegis/secrets/kubeconfig/factory-a.tailscale-ip-tlsname.kubeconfig}"
      ;;
    factory-b)
      echo "${AEGIS_FACTORY_B_DIRECT_KUBECONFIG:-${HOME}/Aegis/.aegis/secrets/kubeconfig/factory-b.tailscale-ip.kubeconfig}"
      ;;
    factory-c)
      echo "${AEGIS_FACTORY_C_DIRECT_KUBECONFIG:-${HOME}/Aegis/.aegis/secrets/kubeconfig/factory-c.tailscale-ip.kubeconfig}"
      ;;
    *)
      echo "unsupported factory: $1" >&2
      return 1
      ;;
  esac
}

check_factory() {
  local factory="$1"
  local kubeconfig
  kubeconfig="$(kubeconfig_for_factory "${factory}")"

  echo "== ${factory} =="
  if [[ ! -f "${kubeconfig}" ]]; then
    echo "WARN: kubeconfig not found: ${kubeconfig}"
    EXIT_CODE=2
    return 0
  fi

  if ! kubectl --kubeconfig "${kubeconfig}" -n "${NAMESPACE}" get namespace "${NAMESPACE}" >/dev/null 2>&1; then
    echo "WARN: cannot reach namespace ${NAMESPACE} with ${kubeconfig}"
    EXIT_CODE=2
    return 0
  fi

  local deployments
  deployments="$(kubectl --kubeconfig "${kubeconfig}" -n "${NAMESPACE}" get deploy \
    -l app.kubernetes.io/component=edge-iot-publisher \
    -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.spec.replicas}{"\t"}{.status.readyReplicas}{"\t"}{.spec.strategy.type}{"\n"}{end}')"

  if [[ -z "${deployments}" ]]; then
    echo "WARN: no edge-iot-publisher Deployment found"
    EXIT_CODE=2
    return 0
  fi

  echo "Deployment	desired	ready	strategy"
  echo "${deployments}"

  local deployment_count
  deployment_count="$(wc -l <<<"${deployments}" | tr -d ' ')"
  if [[ "${deployment_count}" -gt 1 ]]; then
    echo "ERROR: more than one edge-iot-publisher Deployment is present"
    EXIT_CODE=1
  fi

  local ready_pods
  ready_pods="$(kubectl --kubeconfig "${kubeconfig}" -n "${NAMESPACE}" get pods \
    -l app.kubernetes.io/component=edge-iot-publisher \
    --field-selector=status.phase=Running \
    -o name | wc -l | tr -d ' ')"

  echo "Running edge-iot-publisher pods: ${ready_pods}"
  if [[ "${ready_pods}" -gt 1 ]]; then
    echo "ERROR: more than one running edge-iot-publisher pod can cause duplicate publish or MQTT client-id churn"
    EXIT_CODE=1
  fi

  if awk -F '\t' 'NF >= 4 && $4 != "Recreate" { found = 1 } END { exit found ? 0 : 1 }' <<<"${deployments}"; then
    echo "ERROR: at least one edge-iot-publisher Deployment strategy is not Recreate"
    EXIT_CODE=1
  fi
}

require_command kubectl

for factory in "${FACTORIES[@]}"; do
  check_factory "${factory}"
done

cat <<'EOF'

Notes:
- This script checks K3s Deployment/pod safety only.
- It does not SSH into factory-b/c workers. If legacy local publisher systemd
  units were ever installed, verify they are stopped before keeping data
  collection active during Hub downtime.
EOF

exit "${EXIT_CODE}"
