#!/usr/bin/env bash

aegis_terraform_init_backend() {
  local root_dir="$1"

  terraform -chdir="${root_dir}" init -input=false -no-color >/dev/null
}

aegis_terraform_state_list_or_error() {
  local root_dir="$1"

  aegis_terraform_init_backend "${root_dir}" >&2
  terraform -chdir="${root_dir}" state list
}

aegis_terraform_state_has_resources() {
  local root_dir="$1"
  local state_output

  if ! state_output="$(aegis_terraform_state_list_or_error "${root_dir}")"; then
    return 2
  fi

  if [[ -z "${state_output}" ]]; then
    return 1
  fi

  return 0
}

aegis_terraform_require_state_resources() {
  local root_dir="$1"
  local label="${2:-${root_dir}}"
  local state_output

  if ! state_output="$(aegis_terraform_state_list_or_error "${root_dir}" 2>&1)"; then
    echo "${label} Terraform state is not accessible:" >&2
    echo "${state_output}" >&2
    exit 1
  fi

  if [[ -z "${state_output}" ]]; then
    echo "${label} Terraform state is accessible but empty." >&2
    exit 1
  fi
}

aegis_terraform_state_pull_json() {
  local root_dir="$1"

  aegis_terraform_init_backend "${root_dir}" >&2
  terraform -chdir="${root_dir}" state pull
}

aegis_terraform_apply_root() {
  local root_dir="$1"

  cd "${root_dir}"

  export AWS_RETRY_MODE="${AWS_RETRY_MODE:-adaptive}"
  export AWS_MAX_ATTEMPTS="${AWS_MAX_ATTEMPTS:-10}"

  if [[ ! -f terraform.tfvars && -f terraform.tfvars.example ]]; then
    cp terraform.tfvars.example terraform.tfvars
  fi

  terraform init
  terraform validate
  terraform plan -out=tfplan
  terraform apply tfplan
}

aegis_terraform_destroy_root() {
  local root_dir="$1"

  cd "${root_dir}"

  export AWS_RETRY_MODE="${AWS_RETRY_MODE:-adaptive}"
  export AWS_MAX_ATTEMPTS="${AWS_MAX_ATTEMPTS:-10}"

  terraform init
  terraform validate
  terraform destroy
}
