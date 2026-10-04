#!/usr/bin/env bash
set -euo pipefail
ROOT="${REPO_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
[[ -f "$ROOT/demo_3d/config/demo.env" ]] && source "$ROOT/demo_3d/config/demo.env"
PYTHONPATH="$ROOT/demo_3d/tools:${PYTHONPATH:-}" \
  python3 "$ROOT/demo_3d/tools/demo3d_runtime.py" nav_timeout
