#!/usr/bin/env bash
set -euo pipefail
ROOT="${REPO_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
PYTHONPATH="$ROOT/demo_3d/tools:${PYTHONPATH:-}" \
  python3 "$ROOT/demo_3d/tools/preflight_3d.py"
