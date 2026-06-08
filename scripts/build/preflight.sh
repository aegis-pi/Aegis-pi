#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# shellcheck disable=SC1091
source "${REPO_ROOT}/scripts/lib/config.sh"
aegis_load_config "${REPO_ROOT}"
# shellcheck disable=SC1091
source "${REPO_ROOT}/scripts/lib/terraform.sh"

BUILD_FOUNDATION="${BUILD_FOUNDATION:-false}"
BUILD_HUB="${BUILD_HUB:-true}"
BUILD_ADMIN_UI_AFTER_NS="${BUILD_ADMIN_UI_AFTER_NS:-false}"
BUILD_IOT="${BUILD_IOT:-false}"
BUILD_TAILSCALE="${BUILD_TAILSCALE:-}"
DEPLOY_SPOKES="${DEPLOY_SPOKES:-}"
AEGIS_PREFLIGHT_AWS_STATE="${AEGIS_PREFLIGHT_AWS_STATE:-true}"

failures=()

add_failure() {
  failures+=("$1")
}

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    add_failure "missing required command: $1"
  fi
}

run_check() {
  local description="$1"
  shift

  if ! "$@" >/dev/null 2>&1; then
    add_failure "${description}"
  fi
}

check_required_commands() {
  if [[ "${BUILD_FOUNDATION}" == "true" || "${BUILD_DATA_PIPE}" == "true" || \
    "${BUILD_HUB}" == "true" || "${BUILD_ADMIN_UI_AFTER_NS}" == "true" || \
    "${BUILD_IOT}" == "true" ]]; then
    require_command aws
  fi

  if [[ "${BUILD_FOUNDATION}" == "true" || "${BUILD_DATA_PIPE}" == "true" || \
    "${BUILD_HUB}" == "true" || "${BUILD_ADMIN_UI_AFTER_NS}" == "true" ]]; then
    require_command terraform
  fi

  if [[ "${BUILD_HUB}" == "true" || "${BUILD_ADMIN_UI_AFTER_NS}" == "true" || \
    ( "${BUILD_IOT}" == "true" && \
      ( "${BUILD_TAILSCALE}" != "false" || "${DEPLOY_SPOKES}" == "true" ) ) ]]; then
    require_command ansible-playbook
    require_command kubectl
    require_command jq
  fi

  if [[ "${BUILD_HUB}" == "true" || \
    ( "${BUILD_IOT}" == "true" && "${BUILD_TAILSCALE}" != "false" ) ]]; then
    require_command helm
    require_command openssl
  fi

  if [[ "${BUILD_ADMIN_UI_AFTER_NS}" == "true" ]]; then
    require_command curl
    require_command getent
  fi

  if [[ "${BUILD_IOT}" == "true" ]]; then
    require_command jq
    require_command curl
    require_command ssh
    require_command scp
  fi
}

check_aws_identity() {
  if [[ "${BUILD_FOUNDATION}" != "true" && "${BUILD_DATA_PIPE}" != "true" && \
    "${BUILD_HUB}" != "true" && "${BUILD_ADMIN_UI_AFTER_NS}" != "true" && \
    "${BUILD_IOT}" != "true" ]]; then
    return 0
  fi

  run_check "AWS credentials are not usable; aws sts get-caller-identity failed" \
    aws sts get-caller-identity
}

check_hub_inputs() {
  local foundation_root
  local state_status
  foundation_root="${REPO_ROOT}/infra/foundation"

  if [[ "${BUILD_HUB}" != "true" && "${BUILD_ADMIN_UI_AFTER_NS}" != "true" ]]; then
    return 0
  fi

  if [[ "${BUILD_FOUNDATION}" == "true" ]]; then
    return 0
  fi

  state_status=0
  aegis_terraform_state_has_resources "${foundation_root}" || state_status=$?
  if [[ "${state_status}" -eq 1 ]]; then
    add_failure "infra/foundation Terraform state is accessible but empty; build foundation before Hub"
  elif [[ "${state_status}" -eq 2 ]]; then
    add_failure "infra/foundation Terraform state is not accessible; Hub reads Foundation outputs from the S3 backend"
  fi
}

check_admin_ui_inputs() {
  local hub_root
  local state_status
  hub_root="${REPO_ROOT}/infra/hub"

  if [[ "${BUILD_ADMIN_UI_AFTER_NS}" != "true" || "${BUILD_HUB}" == "true" ]]; then
    return 0
  fi

  state_status=0
  aegis_terraform_state_has_resources "${hub_root}" || state_status=$?
  if [[ "${state_status}" -eq 1 ]]; then
    add_failure "infra/hub Terraform state is accessible but empty; run scripts/build/build-hub.sh before --admin-ui-after-ns"
  elif [[ "${state_status}" -eq 2 ]]; then
    add_failure "infra/hub Terraform state is not accessible; run scripts/build/build-hub.sh before --admin-ui-after-ns"
  fi
}

check_tailscale_inputs() {
  local operator_env
  local direct_kubeconfig
  local hub_root
  local state_status

  if [[ "${BUILD_IOT}" != "true" || \
    ( "${BUILD_TAILSCALE}" == "false" && "${DEPLOY_SPOKES}" != "true" ) ]]; then
    return 0
  fi

  hub_root="${REPO_ROOT}/infra/hub"
  if [[ "${BUILD_HUB}" != "true" ]]; then
    state_status=0
    aegis_terraform_state_has_resources "${hub_root}" || state_status=$?
    if [[ "${state_status}" -eq 1 ]]; then
      add_failure "infra/hub Terraform state is accessible but empty; run scripts/build/build-hub.sh before Hub-Spoke Tailscale bootstrap"
    elif [[ "${state_status}" -eq 2 ]]; then
      add_failure "infra/hub Terraform state is not accessible; run scripts/build/build-hub.sh before Hub-Spoke Tailscale bootstrap"
    fi
  fi

  if [[ "${BUILD_TAILSCALE}" == "false" ]]; then
    return 0
  fi

  operator_env="${AEGIS_TAILSCALE_OPERATOR_ENV:-${HOME}/Aegis/.aegis/secrets/tailscale/operator.env}"
  direct_kubeconfig="${AEGIS_FACTORY_A_DIRECT_KUBECONFIG:-${HOME}/Aegis/.aegis/secrets/kubeconfig/factory-a.tailscale-ip-tlsname.kubeconfig}"

  if [[ ! -f "${operator_env}" ]]; then
    add_failure "missing ${operator_env}; set BUILD_TAILSCALE=false to skip Hub-Spoke Tailscale bootstrap"
  elif ! env -i bash -c "set -euo pipefail; set -a; . \"${operator_env}\"; test -n \"\${TAILSCALE_OAUTH_CLIENT_ID:-}\"; test -n \"\${TAILSCALE_OAUTH_CLIENT_SECRET:-}\"" >/dev/null 2>&1; then
    add_failure "${operator_env} must define TAILSCALE_OAUTH_CLIENT_ID and TAILSCALE_OAUTH_CLIENT_SECRET"
  fi

  if [[ ! -f "${direct_kubeconfig}" ]]; then
    add_failure "missing ${direct_kubeconfig}; set BUILD_TAILSCALE=false to skip factory-a ArgoCD cluster Secret bootstrap"
  fi
}

check_hub_state_resource() {
  local description="$1"
  local command="$2"
  local advice="$3"
  local output

  output="$(bash -c "${command}" 2>&1)" && return 0

  add_failure "${description} is in infra/hub Terraform state but AWS read failed: ${output}. ${advice}"
}

check_hub_state_against_aws() {
  local hub_root
  local state_json
  local vpc_id
  local log_group_arn
  local tainted_resources

  if [[ "${BUILD_HUB}" != "true" || "${AEGIS_PREFLIGHT_AWS_STATE}" != "true" ]]; then
    return 0
  fi

  hub_root="${REPO_ROOT}/infra/hub"
  state_json="$(aegis_terraform_state_pull_json "${hub_root}" 2>&1)" || {
    add_failure "infra/hub Terraform state is not accessible for AWS preflight: ${state_json}"
    return 0
  }

  if ! command -v jq >/dev/null 2>&1 || ! command -v aws >/dev/null 2>&1; then
    return 0
  fi

  tainted_resources="$(
    jq -r '
      .resources[]?
      | . as $resource
      | .instances[]?
      | select(.status == "tainted" and (.deposed == null))
      | (($resource.module // "root") + "." + $resource.type + "." + $resource.name + "[" + ((.index_key // 0) | tostring) + "]")
    ' <<<"${state_json}"
  )"
  if [[ -n "${tainted_resources}" ]]; then
    add_failure "infra/hub Terraform state contains tainted resources: ${tainted_resources//$'\n'/, }. Resolve with terraform untaint/import or recreate cleanup before build-all."
  fi

  vpc_id="$(
    jq -r '.resources[]? | select((.module // "root") == "root" and .type == "aws_vpc" and .name == "hub") | .instances[0].attributes.id // empty' \
      <<<"${state_json}"
  )"
  if [[ -n "${vpc_id}" ]]; then
    check_hub_state_resource \
      "VPC ${vpc_id}" \
      "aws ec2 describe-vpcs --region '${AEGIS_AWS_REGION}' --vpc-ids '${vpc_id}'" \
      "If the VPC was deleted outside this state, run destroy/state cleanup before build-all."
  fi

  log_group_arn="$(
    jq -r '.resources[]? | select((.module // "") == "module.eks" and .type == "aws_cloudwatch_log_group" and .name == "this") | .instances[0].attributes.arn // empty' \
      <<<"${state_json}"
  )"
  if [[ -n "${log_group_arn}" ]]; then
    check_hub_state_resource \
      "CloudWatch log group ${log_group_arn}" \
      "aws logs list-tags-for-resource --region '${AEGIS_AWS_REGION}' --resource-arn '${log_group_arn}'" \
      "If the log group was deleted outside this state, run destroy/state cleanup before build-all."
  fi
}

check_required_commands
check_aws_identity
check_hub_inputs
check_admin_ui_inputs
check_tailscale_inputs
check_hub_state_against_aws

if (( ${#failures[@]} > 0 )); then
  echo "Build preflight failed:" >&2
  for failure in "${failures[@]}"; do
    echo "  - ${failure}" >&2
  done
  echo >&2
  echo "To bypass only these checks, set AEGIS_BUILD_PREFLIGHT=false. Bypassing does not fix the underlying dependency." >&2
  exit 1
fi

echo "Build preflight passed."
