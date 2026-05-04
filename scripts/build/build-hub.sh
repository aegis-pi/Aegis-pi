#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
OTP="${1:-}"

if [[ -z "${AWS_SESSION_TOKEN:-}" ]]; then
  if [[ -z "${OTP}" ]]; then
    read -r -p "MFA OTP: " OTP
  fi

  if [[ -z "${OTP}" ]]; then
    echo "MFA OTP is required when AWS_SESSION_TOKEN is not set" >&2
    exit 1
  fi

  if [[ -f "${HOME}/.bashrc" ]]; then
    # shellcheck disable=SC1090
    source "${HOME}/.bashrc"
  fi

  if declare -F setToken >/dev/null 2>&1; then
    setToken "${OTP}"
  elif [[ -x "/home/vicbear/Aegis/.tools/aws-mfa-script/mfa.sh" ]]; then
    /home/vicbear/Aegis/.tools/aws-mfa-script/mfa.sh "${OTP}"
    # shellcheck disable=SC1090
    source "${HOME}/.token_file"
  else
    echo "MFA helper not found. Expected setToken function or /home/vicbear/Aegis/.tools/aws-mfa-script/mfa.sh" >&2
    exit 1
  fi
fi

unset AWS_PROFILE
export AWS_REGION="${AWS_REGION:-ap-south-1}"
export AWS_DEFAULT_REGION="${AWS_DEFAULT_REGION:-${AWS_REGION}}"

cd "${REPO_ROOT}/infra/hub"

if [[ ! -f terraform.tfvars ]]; then
  cp terraform.tfvars.example terraform.tfvars
fi

terraform init
terraform validate
terraform plan -out=tfplan
terraform apply tfplan

cd "${REPO_ROOT}/scripts/ansible"
ansible-playbook -i inventory/hub_eks_dynamic.sh playbooks/hub_argocd_bootstrap.yml
ansible-playbook -i inventory/hub_eks_dynamic.sh playbooks/hub_argocd_verify.yml
