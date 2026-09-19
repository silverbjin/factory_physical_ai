#!/usr/bin/env python3
"""Run TASK-SIM-009's deterministic bounded failure/recovery suite."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))
from simulation_runtime.failure_recovery import run_failure_suite  # noqa: E402


def build_evidence(*, navigation_runtime_factory: object | None = None) -> dict[str, object]:
    suite = run_failure_suite() if navigation_runtime_factory is None else run_failure_suite(
        navigation_runtime_factory=navigation_runtime_factory
    )
    return suite | {"generated_at": datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")}


def main() -> int:
    evidence = build_evidence()
    path = ROOT / "results/simulation/SIM-009_failure_recovery.json"
    path.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n")
    print(json.dumps(evidence, sort_keys=True))
    return 0 if evidence["task_specific_result"] == "SIM_FAILURE_SUITE_READY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
