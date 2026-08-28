#!/usr/bin/env bash
# Non-destructive Phase 0 environment check. It never moves hardware, installs
# packages, contacts model providers, or pulls container/model images.
set -u -o pipefail

RESULT_PATH="${RESULT_PATH:-results/phase0/environment_verification.json}"
mkdir -p "$(dirname "$RESULT_PATH")"

required_failures=0
check_names=()
check_statuses=()
check_details=()

record() {
  local name="$1" status="$2" detail="$3"
  check_names+=("$name")
  check_statuses+=("$status")
  check_details+=("$detail")
  printf '%-6s %s — %s\n' "$status" "$name" "$detail"
  if [[ "$status" == "FAIL" ]]; then
    required_failures=$((required_failures + 1))
  fi
}

command_version() {
  local command_name="$1"
  if command -v "$command_name" >/dev/null 2>&1; then
    local version
    version=$("$command_name" --version 2>&1 | head -n 1 || true)
    record "$command_name" "PASS" "${version:-available}"
  else
    record "$command_name" "WARN" "not found (optional in Phase 0)"
  fi
}

python_import() {
  local module="$1"
  if python3 - "$module" <<'PY' >/dev/null 2>&1
import importlib.util
import sys
sys.exit(0 if importlib.util.find_spec(sys.argv[1]) else 1)
PY
  then
    record "python:${module}" "PASS" "importable"
  else
    record "python:${module}" "WARN" "not installed in current interpreter"
  fi
}

json_escape() {
  local value="$1"
  value=${value//\\/\\\\}
  value=${value//\"/\\\"}
  value=${value//$'\n'/\\n}
  printf '%s' "$value"
}

printf 'Physical AI Phase 0 environment verification\n'
printf 'Generated: %s\n\n' "$(date -u +'%Y-%m-%dT%H:%M:%SZ')"

if [[ -f /etc/os-release ]]; then
  # shellcheck disable=SC1091
  . /etc/os-release
  record "os" "PASS" "${PRETTY_NAME:-unknown}"
else
  record "os" "FAIL" "unable to read /etc/os-release"
fi

if [[ "$(uname -r)" == *microsoft* || "$(uname -r)" == *WSL* ]]; then
  record "wsl" "WARN" "WSL kernel detected; native robot hardware requires a separate validation gate"
else
  record "wsl" "PASS" "native Linux kernel"
fi

command_version git
command_version python3
command_version ros2
command_version docker
command_version node

if command -v ros2 >/dev/null 2>&1 && [[ -n "${ROS_DISTRO:-}" ]]; then
  record "ros_environment" "PASS" "ROS_DISTRO=${ROS_DISTRO}"
elif command -v ros2 >/dev/null 2>&1; then
  record "ros_environment" "WARN" "ros2 exists but ROS_DISTRO is unset"
else
  record "ros_environment" "WARN" "ROS 2 is not installed"
fi

if command -v docker >/dev/null 2>&1; then
  if docker info --format '{{.ServerVersion}}' >/dev/null 2>&1; then
    record "docker_daemon" "PASS" "daemon accessible"
  else
    record "docker_daemon" "WARN" "daemon unavailable or access denied; no image pull attempted"
  fi
fi

if command -v nvidia-smi >/dev/null 2>&1; then
  gpu_line=$(nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader 2>/dev/null | head -n 1)
  gpu_status=$?
  if [[ "$gpu_status" -eq 0 && -n "$gpu_line" ]]; then
    record "gpu" "PASS" "$gpu_line"
  else
    record "gpu" "WARN" "nvidia-smi exists but GPU/NVML is not accessible"
  fi
else
  record "gpu" "WARN" "nvidia-smi not found"
fi

python_import rclpy
python_import torch
python_import lerobot
python_import langgraph
python_import pydantic
python_import sqlalchemy
python_import opentelemetry
python_import prometheus_client

video_count=$(find /dev -maxdepth 1 -type c -name 'video*' -print 2>/dev/null | wc -l | tr -d ' ')
serial_count=$(find /dev -maxdepth 1 \( -name 'ttyUSB*' -o -name 'ttyACM*' \) -print 2>/dev/null | wc -l | tr -d ' ')
if [[ "$video_count" == "0" ]]; then
  record "camera_devices" "WARN" "no /dev/video* device observed"
else
  record "camera_devices" "PASS" "$video_count video device(s) observed; no settings changed"
fi
if [[ "$serial_count" == "0" ]]; then
  record "robot_serial_devices" "WARN" "no /dev/ttyUSB* or /dev/ttyACM* device observed"
else
  record "robot_serial_devices" "PASS" "$serial_count serial device(s) observed; no command sent"
fi

{
  printf '{\n'
  printf '  "schema_version": "1.0",\n'
  printf '  "generated_at": "%s",\n' "$(date -u +'%Y-%m-%dT%H:%M:%SZ')"
  printf '  "host": {"kernel": "%s", "python": "%s"},\n' "$(json_escape "$(uname -r)")" "$(json_escape "$(python3 --version 2>&1)")"
  printf '  "checks": [\n'
  for i in "${!check_names[@]}"; do
    comma=','
    if [[ "$i" -eq $((${#check_names[@]} - 1)) ]]; then comma=''; fi
    printf '    {"name":"%s","status":"%s","detail":"%s"}%s\n' \
      "$(json_escape "${check_names[$i]}")" "${check_statuses[$i]}" "$(json_escape "${check_details[$i]}")" "$comma"
  done
  printf '  ],\n'
  printf '  "required_failures": %s\n' "$required_failures"
  printf '}\n'
} > "$RESULT_PATH"

printf '\nEvidence: %s\n' "$RESULT_PATH"
if [[ "$required_failures" -gt 0 ]]; then
  printf 'FAIL: %s required check(s) failed.\n' "$required_failures"
  exit 1
fi
printf 'PASS: required baseline checks passed; WARN items require their documented gates.\n'
