#!/usr/bin/env bash
set -euo pipefail

REGION="${AWS_REGION:-ap-south-1}"
CLUSTER_NAME="${CLUSTER_NAME:-AEGIS-EKS}"
NAMESPACE="${ARGOCD_NAMESPACE:-argocd}"
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
export AWS_REGION="$REGION"
export AWS_DEFAULT_REGION="${AWS_DEFAULT_REGION:-${AWS_REGION}}"

aws eks update-kubeconfig --region "$REGION" --name "$CLUSTER_NAME"

kubectl -n "$NAMESPACE" get secret argocd-initial-admin-secret \
  -o jsonpath='{.data.password}' | base64 -d
echo
