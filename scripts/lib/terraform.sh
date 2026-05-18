#!/usr/bin/env bash

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
