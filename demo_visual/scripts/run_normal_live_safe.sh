#!/usr/bin/env bash
set -euo pipefail
ROOT="${REPO_ROOT:-$(git rev-parse --show-toplevel)}"; mkdir -p "$ROOT/results/demo"
if [[ -f "$ROOT/scripts/run_simulation_normal_system_e2e.py" ]]; then RUNNER="scripts/run_simulation_normal_system_e2e.py"; CANON="results/simulation/SIM-008_normal_system_e2e.json"; elif [[ -f "$ROOT/scripts/run_simulation_normal_e2e.py" ]]; then RUNNER="scripts/run_simulation_normal_e2e.py"; CANON="results/simulation/SIM-008_normal_e2e.json"; else echo "runner not found" >&2; exit 2; fi
if python3 "$ROOT/$RUNNER" --help 2>&1 | grep -q -- --output; then python3 "$ROOT/$RUNNER" --output "$ROOT/results/demo/SIM-008_normal_e2e_demo.json"; else TMP="$(mktemp -d /tmp/sim008-visual.XXXXXX)"; cleanup(){ git -C "$ROOT" worktree remove "$TMP" --force >/dev/null 2>&1 || true; rm -rf "$TMP"; }; trap cleanup EXIT; git -C "$ROOT" worktree add --detach "$TMP" HEAD >/dev/null; (cd "$TMP"; export PYTHONPATH="$TMP/src:$TMP:${PYTHONPATH:-}"; python3 "$TMP/$RUNNER"); [[ -f "$TMP/$CANON" ]] || { echo "expected Evidence missing" >&2; exit 3; }; cp "$TMP/$CANON" "$ROOT/results/demo/SIM-008_normal_e2e_demo.json"; fi
echo "Demo Evidence: results/demo/SIM-008_normal_e2e_demo.json"
echo "Next: ./demo_visual/scripts/replay_visual.sh normal"
