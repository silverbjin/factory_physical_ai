#!/usr/bin/env bash
set -euo pipefail

demo_die() {
  echo "[DEMO][ERROR] $*" >&2
  exit 2
}

demo_warn() {
  echo "[DEMO][WARN] $*" >&2
}

demo_info() {
  echo "[DEMO] $*"
}

resolve_repo_root() {
  if [[ -n "${REPO_ROOT:-}" ]]; then
    (cd "$REPO_ROOT" && pwd)
    return
  fi
  local here
  here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  if git -C "$here" rev-parse --show-toplevel >/dev/null 2>&1; then
    git -C "$here" rev-parse --show-toplevel
    return
  fi
  if git rev-parse --show-toplevel >/dev/null 2>&1; then
    git rev-parse --show-toplevel
    return
  fi
  demo_die "Repository root not found. Set REPO_ROOT=/path/to/factory_physical_ai_repo."
}

ROOT="$(resolve_repo_root)"
DEMO_DIR="$ROOT/demo"
DEMO_OUT="$ROOT/results/demo"
mkdir -p "$DEMO_OUT"

require_file() {
  [[ -f "$ROOT/$1" ]] || demo_die "Required file missing: $1"
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || demo_die "Required command missing: $1"
}

resolve_sim008_evidence() {
  if [[ -n "${DEMO_SIM008_EVIDENCE:-}" ]]; then
    [[ -f "$ROOT/$DEMO_SIM008_EVIDENCE" ]] || demo_die "DEMO_SIM008_EVIDENCE does not exist: $DEMO_SIM008_EVIDENCE"
    printf '%s\n' "$ROOT/$DEMO_SIM008_EVIDENCE"
    return
  fi
  local found=()
  local p
  for p in \
    results/simulation/SIM-008_normal_system_e2e.json \
    results/simulation/SIM-008_normal_e2e.json
  do
    [[ -f "$ROOT/$p" ]] && found+=("$ROOT/$p")
  done
  if [[ ${#found[@]} -eq 1 ]]; then
    printf '%s\n' "${found[0]}"
  elif [[ ${#found[@]} -eq 0 ]]; then
    demo_die "No SIM-008 canonical Evidence found."
  else
    demo_die "Both SIM-008 Evidence variants exist. Set DEMO_SIM008_EVIDENCE to the acceptance-bound path."
  fi
}

resolve_normal_runner() {
  if [[ -n "${DEMO_NORMAL_RUNNER:-}" ]]; then
    [[ -f "$ROOT/$DEMO_NORMAL_RUNNER" ]] || demo_die "DEMO_NORMAL_RUNNER does not exist: $DEMO_NORMAL_RUNNER"
    printf '%s\n' "$ROOT/$DEMO_NORMAL_RUNNER"
    return
  fi
  local found=()
  local p
  for p in \
    scripts/run_simulation_normal_system_e2e.py \
    scripts/run_simulation_normal_e2e.py
  do
    [[ -f "$ROOT/$p" ]] && found+=("$ROOT/$p")
  done
  if [[ ${#found[@]} -eq 1 ]]; then
    printf '%s\n' "${found[0]}"
  elif [[ ${#found[@]} -eq 0 ]]; then
    demo_die "No canonical SIM-008 runner found."
  else
    demo_die "Both normal E2E runners exist. Set DEMO_NORMAL_RUNNER to the currently accepted runner."
  fi
}

runner_supports_output() {
  local runner="$1"
  python3 "$runner" --help 2>&1 | grep -q -- '--output'
}

run_to_demo_output() {
  local runner="$1"
  local output="$2"
  runner_supports_output "$runner" || demo_die "Runner does not expose --output; refusing to risk canonical Evidence mutation: $runner"
  python3 "$runner" --output "$output"
}

canonical_sim009() {
  printf '%s\n' "$ROOT/results/simulation/SIM-009_failure_recovery.json"
}

canonical_sim010() {
  printf '%s\n' "$ROOT/results/simulation/SIM-010_observability_regression.json"
}

canonical_e2e() {
  printf '%s\n' "$ROOT/results/simulation/SIM-E2E_qualification.json"
}
