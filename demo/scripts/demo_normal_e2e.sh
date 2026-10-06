#!/usr/bin/env bash
set -euo pipefail
source "$(cd "$(dirname "$0")" && pwd)/_demo_common.sh"

mode="${1:---accepted}"
case "$mode" in
  --accepted)
    src="$(resolve_sim008_evidence)"
    demo_info "Showing accepted SIM-008 Evidence: ${src#$ROOT/}"
    python3 "$DEMO_DIR/tools/show_normal_e2e.py" "$src"
    ;;
  --live)
    runner="$(resolve_normal_runner)"
    out="$DEMO_OUT/SIM-008_normal_e2e_demo.json"
    demo_info "Running canonical normal E2E without touching accepted Evidence."
    demo_info "Runner: ${runner#$ROOT/}"
    demo_info "Output: ${out#$ROOT/}"
    run_to_demo_output "$runner" "$out"
    python3 "$DEMO_DIR/tools/show_normal_e2e.py" "$out"
    ;;
  *)
    demo_die "Usage: $0 [--accepted|--live]"
    ;;
esac
