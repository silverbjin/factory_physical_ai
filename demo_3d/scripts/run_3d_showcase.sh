#!/usr/bin/env bash
set -euo pipefail
ROOT="${REPO_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
"$ROOT/demo_3d/scripts/00_preflight_3d.sh"
read -r -p "Normal E2E 3D 시작 [Enter] "
"$ROOT/demo_3d/scripts/01_normal_e2e_3d.sh"
read -r -p "Navigation Timeout 3D 시작 [Enter] "
"$ROOT/demo_3d/scripts/02_navigation_timeout_3d.sh"
read -r -p "Verification Uncertain 3D 시작 [Enter] "
"$ROOT/demo_3d/scripts/03_verification_uncertain_3d.sh"
read -r -p "Final Qualification 3D context 시작 [Enter] "
"$ROOT/demo_3d/scripts/04_final_qualification_3d.sh"
echo "[3D SHOWCASE] complete"
