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

BASELINE_COMMIT = "6909c6cceb727598570f6e170ae8d1d293418c9a"
PROVEN_PREEXISTING_FAILURES = {
    "scripts/codex/test_run_task_orchestrator.py::OrchestratorUnitTests::test_load_model_policy",
    "tests/test_simulation_lane_gate.py::SimulationLaneGateTests::test_canonical_state_reconstructs_sim_go_without_authorizing_lane",
    "tests/test_simulation_lane_gate.py::SimulationLaneGateTests::test_combined_review_commit_rewrite_and_concatenated_operation_fails_closed",
    "tests/test_simulation_lane_gate.py::SimulationLaneGateTests::test_rehashed_unreviewed_runtime_operation_marker_fails_provenance_closed",
}


def main() -> int:
    evidence = build_regression_evidence(ROOT)
    command = [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"]
    environment = os.environ | {"PYTHONDONTWRITEBYTECODE": "1"}
    validation = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False, env=environment)
    match = re.search(r"(\d+) passed", validation.stdout)
    failed_nodes = set(re.findall(r"^FAILED (.+)$", validation.stdout, flags=re.MULTILINE))
    proven_preexisting = validation.returncode != 0 and failed_nodes == PROVEN_PREEXISTING_FAILURES
    evidence["full_repository_regression"] = {
        "command": "PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider",
        "exit_code": validation.returncode, "tests_passed": int(match.group(1)) if match else 0,
        "result": "PASS" if validation.returncode == 0 else "FAIL",
        "baseline_commit": BASELINE_COMMIT,
        "failure_classification": "PASS" if validation.returncode == 0 else ("PROVEN_PREEXISTING" if proven_preexisting else "POSSIBLY_TASK_RELATED"),
        "failed_node_ids": sorted(failed_nodes),
    }
    if validation.returncode != 0:
        if proven_preexisting:
            evidence["full_repository_regression"]["blocking_reason"] = "PROVEN_PREEXISTING_FULL_REGRESSION_FAILURES"
        else:
            evidence["task_specific_result"] = "SIM_OBSERVABILITY_REGRESSION_BLOCKED"
            evidence["full_repository_regression"]["blocking_reason"] = "FULL_REGRESSION_FAILED"
    evidence["generated_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    evidence["source_git_sha"] = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, capture_output=True, check=False).stdout.strip()
    path = ROOT / "results/simulation/SIM-010_observability_regression.json"
    path.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n")
    print(json.dumps(evidence, sort_keys=True))
    return 0 if evidence["task_specific_result"] == "SIM_OBSERVABILITY_REGRESSION_READY" and (validation.returncode == 0 or proven_preexisting) else 1


if __name__ == "__main__":
    raise SystemExit(main())
