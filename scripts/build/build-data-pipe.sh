#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
OTP="${1:-}"

# shellcheck disable=SC1091
source "${REPO_ROOT}/scripts/lib/config.sh"
aegis_load_config "${REPO_ROOT}"
# shellcheck disable=SC1091
source "${REPO_ROOT}/scripts/lib/aws-mfa.sh"
# shellcheck disable=SC1091
source "${REPO_ROOT}/scripts/lib/terraform.sh"
aegis_ensure_aws_mfa "${OTP}"

aegis_terraform_apply_root "${REPO_ROOT}/infra/data-pipeline"

put_risk_alert_secret_value() {
  local file_path="$1"
  local secret_name="$2"
  local label="$3"

  if [[ ! -f "${file_path}" ]]; then
    cat >&2 <<WARN
[WARNING] RiskAlertDispatcher ${label} Slack webhook file not found:
  ${file_path}

The data-pipeline stack was applied, but ${label} Slack alerts will not be able
to send until the secret value is stored in Secrets Manager:
  ${secret_name}
WARN
    return 0
  fi

  chmod 600 "${file_path}"
  aws secretsmanager put-secret-value \
    --secret-id "${secret_name}" \
    --secret-string "file://${file_path}" \
    --query VersionId \
    --output text >/dev/null
  echo "RiskAlertDispatcher ${label} Slack webhook value updated in Secrets Manager (${secret_name})."
}

SECRETS_ROOT="${AEGIS_RISK_ALERT_SECRETS_ROOT:-${REPO_ROOT}/../../.secrets}"

put_risk_alert_secret_value \
  "${AEGIS_RISK_ALERT_SLACK_WEBHOOK_FILE:-${SECRETS_ROOT}/aegis_slack_webhook_url}" \
  "${AEGIS_RISK_ALERT_SLACK_SECRET_NAME:-AEGIS/foundation-mvp/risk-alert/slack-webhook-url}" \
  "cloud"

put_risk_alert_secret_value \
  "${AEGIS_RISK_ALERT_SLACK_WEBHOOK_FACTORY_A_FILE:-${SECRETS_ROOT}/aegis_slack_webhook_factory_a}" \
  "${AEGIS_RISK_ALERT_SLACK_SECRET_FACTORY_A_NAME:-AEGIS/foundation-mvp/risk-alert/slack-webhook/factory-a}" \
  "factory-a"

put_risk_alert_secret_value \
  "${AEGIS_RISK_ALERT_SLACK_WEBHOOK_FACTORY_B_FILE:-${SECRETS_ROOT}/aegis_slack_webhook_factory_b}" \
  "${AEGIS_RISK_ALERT_SLACK_SECRET_FACTORY_B_NAME:-AEGIS/foundation-mvp/risk-alert/slack-webhook/factory-b}" \
  "factory-b"

put_risk_alert_secret_value \
  "${AEGIS_RISK_ALERT_SLACK_WEBHOOK_FACTORY_C_FILE:-${SECRETS_ROOT}/aegis_slack_webhook_factory_c}" \
  "${AEGIS_RISK_ALERT_SLACK_SECRET_FACTORY_C_NAME:-AEGIS/foundation-mvp/risk-alert/slack-webhook/factory-c}" \
  "factory-c"
