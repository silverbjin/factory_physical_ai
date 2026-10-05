#!/usr/bin/env bash
set -euo pipefail
ROOT="${REPO_ROOT:-$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)}"
"$ROOT/demo_3d/scripts/00_preflight_3d.sh"
for step in 01_normal_e2e_3d 02_navigation_timeout_3d 03_verification_uncertain_3d 04_final_qualification_3d; do
  if [[ "${DEMO_NO_WAIT:-0}" != 1 ]]; then read -r -p "Run $step [Enter] "; fi
  "$ROOT/demo_3d/scripts/$step.sh"
done
echo "[3D SHOWCASE] complete"
