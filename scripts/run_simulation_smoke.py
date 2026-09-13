#!/usr/bin/env python3
"""Run the bounded TASK-SIM-002 deterministic smoke suite."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from simulation_runtime import run_smoke_suite  # noqa: E402


def main() -> int:
    print(json.dumps(run_smoke_suite(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
