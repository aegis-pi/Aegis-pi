#!/usr/bin/env bash

aegis_load_config() {
  local repo_root="$1"

  # shellcheck disable=SC1091
  source "${repo_root}/scripts/config/defaults.sh"
}
