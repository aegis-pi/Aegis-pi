#!/usr/bin/env bash

aegis_ensure_aws_mfa() {
  local otp="${1:-}"
  local require_otp="${2:-false}"
  local default_region="${AEGIS_AWS_REGION:-ap-south-1}"

  if [[ -n "${AWS_SESSION_TOKEN:-}" && "${require_otp}" != "true" ]]; then
    unset AWS_PROFILE
    export AWS_REGION="${AWS_REGION:-${default_region}}"
    export AWS_DEFAULT_REGION="${AWS_DEFAULT_REGION:-${AWS_REGION}}"
    return 0
  fi

  if [[ -z "${otp}" ]]; then
    read -r -p "MFA OTP: " otp
  fi

  if [[ -z "${otp}" ]]; then
    echo "MFA OTP is required when AWS_SESSION_TOKEN is not set" >&2
    exit 1
  fi

  if [[ -f "${HOME}/.bashrc" ]]; then
    # shellcheck disable=SC1090
    source "${HOME}/.bashrc"
  fi

  if declare -F setToken >/dev/null 2>&1; then
    setToken "${otp}"
  elif [[ -x "/home/vicbear/Aegis/.tools/aws-mfa-script/mfa.sh" ]]; then
    /home/vicbear/Aegis/.tools/aws-mfa-script/mfa.sh "${otp}"
    # shellcheck disable=SC1090
    source "${HOME}/.token_file"
  else
    echo "MFA helper not found. Expected setToken function or /home/vicbear/Aegis/.tools/aws-mfa-script/mfa.sh" >&2
    exit 1
  fi

  unset AWS_PROFILE
  export AWS_REGION="${AWS_REGION:-${default_region}}"
  export AWS_DEFAULT_REGION="${AWS_DEFAULT_REGION:-${AWS_REGION}}"
}
