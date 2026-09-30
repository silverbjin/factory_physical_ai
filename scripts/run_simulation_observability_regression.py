#!/usr/bin/env python3
"""Generate the TASK-SIM-010 accepted-evidence regression artifact."""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from simulation_runtime.observability_regression import build_regression_evidence  # noqa: E402


def main() -> int:
    evidence = build_regression_evidence(ROOT)
    command = [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"]
    environment = os.environ | {"PYTHONDONTWRITEBYTECODE": "1"}
    validation = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False, env=environment)
    match = re.search(r"(\d+) passed", validation.stdout)
    evidence["full_repository_regression"] = {
        "command": "PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider",
        "exit_code": validation.returncode, "tests_passed": int(match.group(1)) if match else 0,
        "result": "PASS" if validation.returncode == 0 else "FAIL",
    }
    if validation.returncode != 0:
        evidence["task_specific_result"] = "SIM_OBSERVABILITY_REGRESSION_BLOCKED"
        evidence["full_repository_regression"]["blocking_reason"] = "FULL_REGRESSION_FAILED"
    evidence["generated_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    evidence["source_git_sha"] = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, capture_output=True, check=False).stdout.strip()
    path = ROOT / "results/simulation/SIM-010_observability_regression.json"
    path.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n")
    print(json.dumps(evidence, sort_keys=True))
    return 0 if evidence["task_specific_result"] == "SIM_OBSERVABILITY_REGRESSION_READY" and validation.returncode == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
