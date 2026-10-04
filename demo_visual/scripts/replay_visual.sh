#!/usr/bin/env bash
set -euo pipefail
ROOT="${REPO_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
SC="${1:-normal}"; shift || true
exec python3 "$ROOT/demo_visual/demo_replay.py" "$SC" --repo-root "$ROOT" "$@"
