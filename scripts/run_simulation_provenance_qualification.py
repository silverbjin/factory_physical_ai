#!/usr/bin/env python3
"""Fail-closed canonical runner for TASK-SIM-Q01 qualification Evidence."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable, Mapping

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from simulation_runtime.provenance_qualification import (
    QualificationSubject,
    aggregate_qualification_evidence,
    collect_sim004_execution_result,
    collect_sim005_execution_result,
    collect_sim007_profile_qualifications,
    collect_sim008_execution_result,
    collect_sim009_execution_result,
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


def live_adapters(
    *,
    sim004_supplier: Callable[[str], Any] | None = None,
    sim005_supplier: Callable[[str], Any] | None = None,
    sim008_supplier: Callable[[], Any] | None = None,
) -> dict[str, Callable[..., Any]]:
    """Return canonical live suppliers; absent task paths are never fabricated."""
    if sim004_supplier is None:
        from scripts.q01_execution_adapters import run_sim004_qualification
        sim004_supplier = run_sim004_qualification
    if sim005_supplier is None:
        from scripts.q01_execution_adapters import run_sim005_qualification
        sim005_supplier = run_sim005_qualification
    if sim008_supplier is None:
        from scripts.q01_execution_adapters import run_sim008_qualification
        sim008_supplier = run_sim008_qualification
    return {
        "TASK-SIM-004": sim004_supplier,
        "TASK-SIM-005": sim005_supplier,
        "TASK-SIM-008": sim008_supplier,
    }


def required_subject_manifest(bindings: dict[str, object]) -> tuple[str, ...]:
    """Derive Q01's explicit deterministic subject manifest from frozen Evidence."""
    required = set(REQUIRED_SUBJECT_IDS)
    sim005 = getattr(bindings["TASK-SIM-005"], "evidence")["scenarios"]
    for row in sim005:
        if isinstance(row, dict) and isinstance(row.get("scenario"), str):
            required.add(f"q01-sim005-{row['scenario']}")
    sim009 = getattr(bindings["TASK-SIM-009"], "evidence")["scenarios"]
    for row in sim009:
        if isinstance(row, dict) and row.get("backend") in {"gazebo_navigation", "mujoco"} and isinstance(row.get("id"), str):
            required.add(f"q01-sim009-{row['id']}")
    return tuple(sorted(required))


def _operation_template(subject_id: str, binding: Any) -> QualificationSubject:
    """Create an unpublished routing template; collectors replace all run-local fields."""
    task_id = binding.task_id
    if task_id == "TASK-SIM-004":
        scenario_id = {
            "q01-sim004-success-time": "success",
            "q01-sim004-blocked-time": "blocked",
            "q01-sim004-timeout-reconciliation-time": "timeout_reconciliation",
        }[subject_id]
        backend_id = "gazebo"
    elif task_id == "TASK-SIM-005":
        scenario_id, backend_id = subject_id.removeprefix("q01-sim005-"), "mujoco"
    elif task_id == "TASK-SIM-008":
        scenario_id, backend_id = str(binding.evidence["scenario"]["scenario_id"]), "gazebo"
    elif task_id == "TASK-SIM-009":
        scenario_id = subject_id.removeprefix("q01-sim009-")
        row = next(row for row in binding.evidence["scenarios"] if row.get("id") == scenario_id)
        backend_id = str(row["backend"])
    else:
        raise ValueError("UNKNOWN_QUALIFICATION_TASK")
    return QualificationSubject(
        subject_id=subject_id, record_kind="operation_run", claim_scope="run_local",
        predecessor_binding={"task_id": binding.task_id, "accepted_commit": binding.accepted_commit, "evidence_path": binding.evidence_path, "evidence_sha256": binding.evidence_sha256},
        qualification_run_id=subject_id, scenario_id=scenario_id, backend_id=backend_id,
        component_version="qualification-pending", configuration_provenance={"routing_placeholder": "0" * 64},
        world_model_provenance={"routing_placeholder": "1" * 64}, timing={"simulation_time": 0.0}, semantic_outcome={},
    )


def collect_qualification_subjects(
    bindings: Mapping[str, Any], adapters: Mapping[str, Callable[..., Any]],
) -> list[QualificationSubject]:
    """Route explicit adapter output through task-owned collectors; never fill missing runs."""
    subjects = collect_sim007_profile_qualifications(ROOT, bindings["TASK-SIM-007"])
    for subject_id in required_subject_manifest(dict(bindings)):
        if subject_id.startswith("q01-sim007-"):
            continue
        if subject_id.startswith("q01-sim004-"):
            adapter = adapters.get("TASK-SIM-004")
            raw = adapter(_operation_template(subject_id, bindings["TASK-SIM-004"]).scenario_id) if adapter else None
            if raw is not None:
                subjects.append(collect_sim004_execution_result(_operation_template(subject_id, bindings["TASK-SIM-004"]), raw))
        elif subject_id.startswith("q01-sim005-"):
            template = _operation_template(subject_id, bindings["TASK-SIM-005"])
            adapter = adapters.get("TASK-SIM-005")
            raw = adapter(template.scenario_id) if adapter else None
            if raw is not None:
                subjects.append(collect_sim005_execution_result(template, raw))
        elif subject_id == "q01-sim008-normal-system-authority":
            template = _operation_template(subject_id, bindings["TASK-SIM-008"])
            adapter = adapters.get("TASK-SIM-008")
            raw = adapter() if adapter else None
            if raw is not None:
                subjects.append(collect_sim008_execution_result(template, raw))
        elif subject_id.startswith("q01-sim009-"):
            template = _operation_template(subject_id, bindings["TASK-SIM-009"])
            adapter = adapters.get("TASK-SIM-009")
            rows = adapter() if adapter else None
            raw = rows.get(template.scenario_id) if isinstance(rows, Mapping) else None
            if raw is not None:
                subjects.append(collect_sim009_execution_result(template, raw))
    identities = [subject.subject_id for subject in subjects]
    if len(identities) != len(set(identities)):
        raise ValueError("DUPLICATE_QUALIFICATION_SUBJECT")
    return sorted(subjects, key=lambda subject: subject.subject_id)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "results/simulation/SIM-Q01_provenance_qualification.json")
    parser.add_argument("--report", type=Path, default=ROOT / "docs/simulation/SIM-Q01_provenance_qualification.md")
    args = parser.parse_args()
    bindings = {}
    for task_id, evidence_path in FROZEN.items():
        acceptance = json.loads((ROOT / f"results/reviews/{task_id.removeprefix('TASK-')}_acceptance.json").read_text())
        bindings[task_id] = resolve_predecessor_binding(ROOT, task_id, acceptance, evidence_path)
    subjects = collect_qualification_subjects(bindings, live_adapters())
    source_git_sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    evidence = aggregate_qualification_evidence(subjects, source_git_sha, required_subject_ids=set(required_subject_manifest(bindings)))
    write_qualification_artifacts(evidence, args.output, args.report)
    print(json.dumps(evidence, sort_keys=True))
    return 0 if evidence["task_specific_result"] == "SIM_PROVENANCE_QUALIFICATION_READY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
