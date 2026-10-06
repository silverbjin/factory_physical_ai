#!/usr/bin/env bash
set -euo pipefail
source "$(cd "$(dirname "$0")" && pwd)/_demo_common.sh"

mode="${1:---accepted}"
target="SIM009-VERIFY-UNCERTAIN"

case "$mode" in
  --accepted)
    src="$(canonical_sim009)"
    require_file "results/simulation/SIM-009_failure_recovery.json"
    ;;
  --live-suite)
    "$DEMO_DIR/scripts/demo_failure_suite.sh"
    src="$DEMO_OUT/SIM-009_failure_recovery_demo.json"
    ;;
  *)
    demo_die "Usage: $0 [--accepted|--live-suite]"
    ;;
esac

demo_info "Scenario: $target"
python3 "$DEMO_DIR/tools/show_sim009_scenario.py" "$src" "$target"
