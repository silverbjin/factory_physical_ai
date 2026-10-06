#!/usr/bin/env bash
set -euo pipefail
source "$(cd "$(dirname "$0")" && pwd)/_demo_common.sh"

mode="${1:---portfolio}"

pause_if_needed() {
  if [[ "${DEMO_INTERACTIVE:-0}" == "1" ]]; then
    read -r -p "Press Enter to continue..."
  fi
}

case "$mode" in
  --portfolio)
    "$DEMO_DIR/scripts/demo_preflight.sh"
    pause_if_needed
    "$DEMO_DIR/scripts/demo_normal_e2e.sh" --accepted
    pause_if_needed
    "$DEMO_DIR/scripts/demo_navigation_timeout.sh" --accepted
    pause_if_needed
    "$DEMO_DIR/scripts/demo_verification_uncertain.sh" --accepted
    pause_if_needed
    "$DEMO_DIR/scripts/demo_evidence_summary.sh"
    pause_if_needed
    "$DEMO_DIR/scripts/demo_qualification.sh" --live
    ;;
  --technical-live)
    "$DEMO_DIR/scripts/demo_preflight.sh"
    pause_if_needed
    "$DEMO_DIR/scripts/demo_normal_e2e.sh" --live
    pause_if_needed
    "$DEMO_DIR/scripts/demo_failure_suite.sh"
    pause_if_needed
    python3 "$DEMO_DIR/tools/show_sim009_scenario.py" \
      "$DEMO_OUT/SIM-009_failure_recovery_demo.json" SIM009-NAV-TIMEOUT-RETRY
    pause_if_needed
    python3 "$DEMO_DIR/tools/show_sim009_scenario.py" \
      "$DEMO_OUT/SIM-009_failure_recovery_demo.json" SIM009-VERIFY-UNCERTAIN
    pause_if_needed
    "$DEMO_DIR/scripts/demo_qualification.sh" --live
    ;;
  *)
    demo_die "Usage: $0 [--portfolio|--technical-live]"
    ;;
esac
