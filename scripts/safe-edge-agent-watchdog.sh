#!/usr/bin/env bash
set -euo pipefail

SERVICE_NAME="${SERVICE_NAME:-k3s-agent}"
MASTER_HOST="${MASTER_HOST:-10.10.10.10}"
MASTER_PORT="${MASTER_PORT:-6443}"
STATE_DIR="${STATE_DIR:-/var/lib/safe-edge}"
STATE_FILE="${STATE_FILE:-$STATE_DIR/agent-watchdog.state}"
LOG_TAG="${LOG_TAG:-safe-edge-agent-watchdog}"

BOOT_GRACE_SECONDS="${BOOT_GRACE_SECONDS:-300}"
CHECK_RESTART_ATTEMPTS="${CHECK_RESTART_ATTEMPTS:-2}"
RESTART_WAIT_SECONDS="${RESTART_WAIT_SECONDS:-15}"
MAX_UNHEALTHY_SECONDS="${MAX_UNHEALTHY_SECONDS:-90}"
REBOOT_COOLDOWN_SECONDS="${REBOOT_COOLDOWN_SECONDS:-1800}"

now="$(date +%s)"
mkdir -p "$STATE_DIR"

log() {
  logger -t "$LOG_TAG" "$*"
  printf '%s %s\n' "$(date -Is)" "$*"
}

uptime_seconds() {
  cut -d. -f1 /proc/uptime
}

load_state() {
  first_failure=0
  attempts=0
  last_reboot=0
  reason=""

  if [[ -f "$STATE_FILE" ]]; then
    # shellcheck disable=SC1090
    source "$STATE_FILE"
  fi
}

save_state() {
  cat > "$STATE_FILE" <<EOF
first_failure=$first_failure
attempts=$attempts
last_reboot=$last_reboot
reason="$reason"
EOF
}

clear_failure_state() {
  last_reboot_saved=0
  if [[ -f "$STATE_FILE" ]]; then
    # shellcheck disable=SC1090
    source "$STATE_FILE"
    last_reboot_saved="${last_reboot:-0}"
  fi

  first_failure=0
  attempts=0
  last_reboot="$last_reboot_saved"
  reason=""
  save_state
}

agent_active() {
  systemctl is-active --quiet "$SERVICE_NAME"
}

master_reachable() {
  timeout 3 bash -c "cat < /dev/null > /dev/tcp/$MASTER_HOST/$MASTER_PORT" >/dev/null 2>&1
}

boot_age="$(uptime_seconds)"
if (( boot_age < BOOT_GRACE_SECONDS )); then
  log "SKIP: boot grace period active (${boot_age}s < ${BOOT_GRACE_SECONDS}s)"
  exit 0
fi

agent_ok=0
network_ok=0

if agent_active; then
  agent_ok=1
fi

if master_reachable; then
  network_ok=1
fi

if (( agent_ok == 1 && network_ok == 1 )); then
  clear_failure_state
  log "OK: $SERVICE_NAME active and master ${MASTER_HOST}:${MASTER_PORT} reachable"
  exit 0
fi

load_state

if (( first_failure == 0 )); then
  first_failure="$now"
  attempts=0
fi

if (( agent_ok == 0 && network_ok == 0 )); then
  reason="agent_inactive_and_master_unreachable"
elif (( agent_ok == 0 )); then
  reason="agent_inactive"
else
  reason="master_unreachable"
fi

elapsed=$(( now - first_failure ))
log "WARN: unhealthy reason=$reason elapsed=${elapsed}s attempts=$attempts"

if (( agent_ok == 0 && attempts < CHECK_RESTART_ATTEMPTS )); then
  attempts=$(( attempts + 1 ))
  save_state
  log "ACTION: restarting $SERVICE_NAME attempt=$attempts"
  systemctl restart "$SERVICE_NAME" || true
  sleep "$RESTART_WAIT_SECONDS"
  exit 0
fi

save_state

if (( elapsed < MAX_UNHEALTHY_SECONDS )); then
  log "WAIT: unhealthy duration below reboot threshold (${elapsed}s < ${MAX_UNHEALTHY_SECONDS}s)"
  exit 0
fi

if (( last_reboot > 0 && now - last_reboot < REBOOT_COOLDOWN_SECONDS )); then
  log "SKIP: reboot cooldown active ($(( now - last_reboot ))s < ${REBOOT_COOLDOWN_SECONDS}s)"
  exit 0
fi

last_reboot="$now"
save_state
log "FENCE: rebooting node after unhealthy reason=$reason elapsed=${elapsed}s"
systemctl reboot
