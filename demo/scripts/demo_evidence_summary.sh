#!/usr/bin/env bash
set -euo pipefail
source "$(cd "$(dirname "$0")" && pwd)/_demo_common.sh"

require_file "results/simulation/SIM-010_observability_regression.json"
demo_info "SIM-010 observability / replay / regression summary"
python3 "$DEMO_DIR/tools/show_sim010.py" "$(canonical_sim010)"
