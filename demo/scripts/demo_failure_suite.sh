#!/usr/bin/env bash
set -euo pipefail
source "$(cd "$(dirname "$0")" && pwd)/_demo_common.sh"

runner="$ROOT/scripts/run_simulation_failure_suite.py"
require_file "scripts/run_simulation_failure_suite.py"
out="$DEMO_OUT/SIM-009_failure_recovery_demo.json"

demo_info "Running full bounded SIM-009 failure suite."
demo_info "Accepted SIM-009 Evidence will NOT be overwritten."
run_to_demo_output "$runner" "$out"
demo_info "Demo Evidence: ${out#$ROOT/}"
python3 "$DEMO_DIR/tools/show_sim009_scenario.py" "$out" --list
