#!/usr/bin/env bash
set -euo pipefail
ROOT="${REPO_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
exec python3 "$ROOT/demo_3d/tools/hud_server.py" --repo-root "$ROOT"
