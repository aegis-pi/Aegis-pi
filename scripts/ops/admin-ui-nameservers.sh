#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# shellcheck disable=SC1091
source "${REPO_ROOT}/scripts/lib/config.sh"
aegis_load_config "${REPO_ROOT}"

OUTPUT_FILE="${ADMIN_UI_NAMESERVERS_FILE:-${REPO_ROOT}/secret/admin-ui-nameservers.txt}"
TERRAFORM_ROOT="${REPO_ROOT}/infra/hub"

if ! command -v terraform >/dev/null 2>&1; then
  echo "terraform command not found" >&2
  exit 1
fi

if ! command -v jq >/dev/null 2>&1; then
  echo "jq command not found" >&2
  exit 1
fi

outputs_json="$(terraform -chdir="${TERRAFORM_ROOT}" output -json)"
domain="$(jq -r '.admin_ui_domain_name.value // empty' <<<"${outputs_json}")"
hosted_zone_id="$(jq -r '.admin_ui_route53_zone_id.value // empty' <<<"${outputs_json}")"
argocd_host="$(jq -r '.admin_ui_argocd_host.value // empty' <<<"${outputs_json}")"
grafana_host="$(jq -r '.admin_ui_grafana_host.value // empty' <<<"${outputs_json}")"
certificate_arn="$(jq -r '.admin_ui_certificate_arn.value // empty' <<<"${outputs_json}")"

mapfile -t name_servers < <(jq -r '.admin_ui_route53_name_servers.value[]? // empty' <<<"${outputs_json}")

if [[ -z "${domain}" || -z "${hosted_zone_id}" || "${#name_servers[@]}" -eq 0 ]]; then
  echo "admin UI Route53 outputs are not available. Run infra/hub Terraform apply first." >&2
  exit 1
fi

mkdir -p "$(dirname "${OUTPUT_FILE}")"

{
  echo "Domain: ${domain}"
  echo "Route53 Hosted Zone ID: ${hosted_zone_id}"
  echo "ArgoCD Host: ${argocd_host}"
  echo "Grafana Host: ${grafana_host}"
  echo "ACM Certificate ARN: ${certificate_arn}"
  echo "Generated At: $(date '+%Y-%m-%d %H:%M:%S %Z')"
  echo
  echo "Set these name servers in Gabia:"
  echo
  printf '%s\n' "${name_servers[@]}"
} >"${OUTPUT_FILE}"

chmod 600 "${OUTPUT_FILE}"
echo "Admin UI Route53 name servers written to ${OUTPUT_FILE}"
echo
echo "Set these name servers in Gabia for ${domain}:"
echo
printf '%s\n' "${name_servers[@]}"
echo
echo "After Gabia NS delegation is saved, run:"
echo
echo "  scripts/build/build-admin-ui-after-ns.sh"
