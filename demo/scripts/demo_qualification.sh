#!/usr/bin/env bash
set -euo pipefail
source "$(cd "$(dirname "$0")" && pwd)/_demo_common.sh"

mode="${1:---live}"
verifier="$ROOT/scripts/verify_simulation_e2e_qualification.py"
require_file "scripts/verify_simulation_e2e_qualification.py"

case "$mode" in
  --accepted)
    require_file "results/simulation/SIM-E2E_qualification.json"
    require_file "results/reviews/SIM-E2E_acceptance.json"
    demo_info "Accepted final qualification Evidence"
    python3 "$DEMO_DIR/tools/show_qualification.py" "$(canonical_e2e)"
    demo_info "Independent acceptance artifact: results/reviews/SIM-E2E_acceptance.json"
    ;;
  --live)
    out="$DEMO_OUT/SIM-E2E_qualification_demo.json"
    demo_info "Running final read-only qualification against canonical accepted sources."
    demo_info "Writing only demo output: ${out#$ROOT/}"
    if python3 "$verifier" --help 2>&1 | grep -q -- '--output'; then
      set +e
      decision="$(python3 "$verifier" --output "$out")"
      rc=$?
      set -e
    else
      demo_die "Verifier lacks --output; refusing to risk canonical result mutation."
    fi
    printf '%s\n' "$decision"
    [[ $rc -eq 0 ]] || demo_die "Verifier execution failed with exit code $rc"
    if [[ "$decision" != "SIM_E2E_QUALIFIED" && "$decision" != "SIM_E2E_NOT_QUALIFIED" ]]; then
      demo_die "Unexpected stdout. Expected exactly one gate decision line."
    fi
    [[ -f "$out" ]] || demo_die "Verifier did not create demo Evidence: $out"
    python3 "$DEMO_DIR/tools/show_qualification.py" "$out"
    ;;
  *)
    demo_die "Usage: $0 [--live|--accepted]"
    ;;
esac
