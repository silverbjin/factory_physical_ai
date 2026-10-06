#!/usr/bin/env bash
set -euo pipefail
ROOT="${REPO_ROOT:-$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)}"
PYTHONPATH="$ROOT/demo_3d/tools:${PYTHONPATH:-}" python3 "$ROOT/demo_3d/tools/verify_3d_runtime.py" "$@"
