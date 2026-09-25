#!/usr/bin/env python3
"""Fail-closed canonical runner for TASK-SIM-Q01 qualification Evidence."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from simulation_runtime.provenance_qualification import (
    aggregate_qualification_evidence,
    collect_sim007_profile_qualifications,
    resolve_predecessor_binding,
    write_qualification_artifacts,
)

FROZEN = {
    "TASK-SIM-004": "results/simulation/SIM-004_navigation_backend.json",
    "TASK-SIM-005": "results/simulation/SIM-005_mujoco_vla_backend.json",
    "TASK-SIM-007": "results/simulation/SIM-007_mission_integration.json",
    "TASK-SIM-008": "results/simulation/SIM-008_normal_system_e2e.json",
    "TASK-SIM-009": "results/simulation/SIM-009_failure_recovery.json",
}
REQUIRED_SUBJECT_IDS = frozenset({
    "q01-sim004-success-time", "q01-sim004-blocked-time", "q01-sim004-timeout-reconciliation-time",
    "q01-sim007-deterministic", "q01-sim007-navigation_physics", "q01-sim007-manipulation_physics", "q01-sim007-system",
    "q01-sim008-normal-system-authority",
})


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "results/simulation/SIM-Q01_provenance_qualification.json")
    parser.add_argument("--report", type=Path, default=ROOT / "docs/simulation/SIM-Q01_provenance_qualification.md")
    args = parser.parse_args()
    bindings = {}
    for task_id, evidence_path in FROZEN.items():
        acceptance = json.loads((ROOT / f"results/reviews/{task_id.removeprefix('TASK-')}_acceptance.json").read_text())
        bindings[task_id] = resolve_predecessor_binding(ROOT, task_id, acceptance, evidence_path)
    subjects = collect_sim007_profile_qualifications(ROOT, bindings["TASK-SIM-007"])
    source_git_sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    evidence = aggregate_qualification_evidence(subjects, source_git_sha, required_subject_ids=set(REQUIRED_SUBJECT_IDS))
    write_qualification_artifacts(evidence, args.output, args.report)
    print(json.dumps(evidence, sort_keys=True))
    return 0 if evidence["task_specific_result"] == "SIM_PROVENANCE_QUALIFICATION_READY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
