#!/usr/bin/env bash
set -euo pipefail
ROOT="${REPO_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
echo "브라우저 Dashboard를 별도 터미널에서 먼저 실행하세요: ./demo_visual/scripts/launch_dashboard.sh"
read -r -p "Normal E2E [Enter] "
"$ROOT/demo_visual/scripts/replay_visual.sh" normal --delay .8
read -r -p "Navigation Timeout [Enter] "
"$ROOT/demo_visual/scripts/replay_visual.sh" nav_timeout --delay .9
read -r -p "Verification Uncertain [Enter] "
"$ROOT/demo_visual/scripts/replay_visual.sh" verify_uncertain --delay .9
read -r -p "Final Qualification [Enter] "
"$ROOT/demo_visual/scripts/replay_visual.sh" qualification --delay .7
