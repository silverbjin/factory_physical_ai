#!/usr/bin/env bash
set -euo pipefail
source "$(cd "$(dirname "$0")" && pwd)/_demo_common.sh"

demo_info "Repository: $ROOT"
require_cmd python3
require_cmd git

for p in \
  results/reviews/SIM-008_acceptance.json \
  results/reviews/SIM-009_acceptance.json \
  results/reviews/SIM-010_acceptance.json \
  results/reviews/SIM-E2E_acceptance.json \
  results/simulation/SIM-009_failure_recovery.json \
  results/simulation/SIM-010_observability_regression.json \
  results/simulation/SIM-E2E_qualification.json \
  scripts/verify_simulation_e2e_qualification.py
do
  require_file "$p"
done

sim008="$(resolve_sim008_evidence)"
normal_runner="$(resolve_normal_runner)"
demo_info "SIM-008 Evidence: ${sim008#$ROOT/}"
demo_info "SIM-008 runner:   ${normal_runner#$ROOT/}"

dirty="$(git -C "$ROOT" status --porcelain -- results/simulation results/reviews || true)"
if [[ -n "$dirty" ]]; then
  echo "$dirty" >&2
  demo_die "Canonical results/simulation or results/reviews is dirty. Do not demo until accepted artifacts are restored."
fi

demo_info "Canonical Evidence/acceptance tree is clean."
demo_info "Demo outputs will be written only under results/demo/."
demo_info "Preflight PASS."
