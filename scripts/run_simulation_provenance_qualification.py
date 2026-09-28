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
sys.path.insert(0, str(ROOT))
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
    "TASK-SIM-004": {"task_id": "TASK-SIM-004", "accepted_commit": "b7e8266abd17f48c18cca94d9433db50fd55464d", "evidence_path": "results/simulation/SIM-004_navigation_backend.json", "evidence_sha256": "b4c0ce91dde6c2f92c57ea6a227149362279993dee0dec4fd1ab12877e73f1d9", "task_specific_result": "SIM_NAVIGATION_BACKEND_READY"},
    "TASK-SIM-005": {"task_id": "TASK-SIM-005", "accepted_commit": "542514a4d10bc03087834e8a5f672d53afe6aa21", "evidence_path": "results/simulation/SIM-005_mujoco_vla_backend.json", "evidence_sha256": "f4d41fdb1f13978e1b1e5c91b95e31b38a69825a0d432a8284ff7731a3beb84f", "task_specific_result": "SIM_MANIPULATION_BACKEND_READY"},
    "TASK-SIM-007": {"task_id": "TASK-SIM-007", "accepted_commit": "228eb7745aa05c230e1b272184601b5afd53853b", "evidence_path": "results/simulation/SIM-007_mission_integration.json", "evidence_sha256": "7247f8db76c874e533f615f1c8c3f32febb7a7e2377790ff05e3e93320531711", "task_specific_result": "SIM_MISSION_INTEGRATION_BLOCKED"},
    "TASK-SIM-008": {"task_id": "TASK-SIM-008", "accepted_commit": "ea91e0c16412e20c8cae66355a1a39129919dd42", "evidence_path": "results/simulation/SIM-008_normal_system_e2e.json", "evidence_sha256": "ebf0ef0a27114e3c04fa6bec05aa3eef792fdfc282d2be009640bac7ecc26290", "task_specific_result": "SIM_NORMAL_E2E_READY"},
    "TASK-SIM-009": {"task_id": "TASK-SIM-009", "accepted_commit": "67bde0e1f29c3f974bf3f0b29dff3f3aaa38e5be", "evidence_path": "results/simulation/SIM-009_failure_recovery.json", "evidence_sha256": "91d10e5bb4fb7ca1b62c325885bec276c6ef6231c6baa0424f3213702be3216e", "task_specific_result": "SIM_FAILURE_SUITE_READY"},
}
MIN_SCOPE_PATH = ROOT / "configs/simulation/min_q01_scope.json"


def live_adapters(
    *,
    sim008_supplier: Callable[[], Any] | None = None,
    sim009_supplier: Callable[[], Any] | None = None,
) -> dict[str, Callable[..., Any]]:
    """Return the only live suppliers admitted by the frozen MIN-Q01 scope."""
    if sim008_supplier is None:
        from scripts.q01_execution_adapters import run_sim008_qualification
        sim008_supplier = run_sim008_qualification
    if sim009_supplier is None:
        from scripts.q01_execution_adapters import run_sim009_qualification
        sim009_supplier = run_sim009_qualification
    return {
        "TASK-SIM-008": sim008_supplier,
        "TASK-SIM-009": sim009_supplier,
    }


def min_q01_scope() -> Mapping[str, Any]:
    """Load the frozen machine-readable MIN-Q01 contract, not legacy Evidence rows."""
    scope = json.loads(MIN_SCOPE_PATH.read_text(encoding="utf-8"))
    subjects = scope.get("required_operation_subjects")
    counts = scope.get("required_operation_subject_counts")
    if (scope.get("scope_id"), scope.get("task_contract")) != ("MIN-Q01", "TASK-SIM-Q01-MIN"):
        raise ValueError("INVALID_MIN_Q01_SCOPE")
    if not isinstance(subjects, list) or not isinstance(counts, Mapping):
        raise ValueError("INVALID_MIN_Q01_SCOPE")
    identities = [row.get("subject_id") for row in subjects if isinstance(row, Mapping)]
    if len(subjects) != 11 or len(identities) != 11 or len(set(identities)) != 11:
        raise ValueError("INVALID_MIN_Q01_SCOPE")
    if counts != {"TASK-SIM-008": 1, "TASK-SIM-009": 10, "total": 11}:
        raise ValueError("INVALID_MIN_Q01_SCOPE")
    if any(not isinstance(identity, str) or not identity.startswith(("q01-sim008-", "q01-sim009-")) for identity in identities):
        raise ValueError("MIN_Q01_SCOPE_REOPEN_REQUIRED")
    return scope


def required_subject_manifest(bindings: Mapping[str, Any] | None = None) -> tuple[str, ...]:
    """Return exactly the eleven frozen MIN-Q01 operation subjects."""
    scope = min_q01_scope()
    rows = scope["required_operation_subjects"]
    if bindings is not None:
        for row in rows:
            assert isinstance(row, Mapping)
            binding = bindings.get(row["predecessor_task_id"])
            if binding is None:
                raise ValueError("MISSING_MIN_Q01_PREDECESSOR")
            if row["predecessor_task_id"] == "TASK-SIM-009":
                scenarios = getattr(binding, "evidence").get("scenarios")
                if not isinstance(scenarios, list) or not any(item.get("id") == row["scenario_id"] for item in scenarios if isinstance(item, Mapping)):
                    raise ValueError("MIN_Q01_SCENARIO_BINDING_MISMATCH")
    return tuple(row["subject_id"] for row in rows)


def _operation_template(subject_id: str, binding: Any) -> QualificationSubject:
    """Create an unpublished routing template; collectors replace all run-local fields."""
    task_id = binding.task_id
    if task_id == "TASK-SIM-008":
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
    """Route only MIN-Q01 run-local subjects; excluded paths never execute here."""
    subjects: list[QualificationSubject] = []
    supplier_results: dict[str, Any] = {}

    def supplied(task_id: str) -> Any:
        if task_id not in supplier_results:
            adapter = adapters.get(task_id)
            if adapter is None:
                raise ValueError(f"MISSING_LIVE_SUPPLIER:{task_id}")
            supplier_results[task_id] = adapter()
        return supplier_results[task_id]

    for subject_id in required_subject_manifest(dict(bindings)):
        if subject_id == "q01-sim008-normal-system-authority":
            template = _operation_template(subject_id, bindings["TASK-SIM-008"])
            raw = supplied("TASK-SIM-008")
            if raw is None:
                raise ValueError("MISSING_LIVE_QUALIFICATION_RESULT:SIM-008")
            subjects.append(collect_sim008_execution_result(template, raw))
        elif subject_id.startswith("q01-sim009-"):
            template = _operation_template(subject_id, bindings["TASK-SIM-009"])
            rows = supplied("TASK-SIM-009")
            raw = rows.get(template.scenario_id) if isinstance(rows, Mapping) else None
            if raw is None:
                raise ValueError(f"MISSING_LIVE_QUALIFICATION_RESULT:{template.scenario_id}")
            subjects.append(collect_sim009_execution_result(template, raw))
    identities = [subject.subject_id for subject in subjects]
    if len(identities) != len(set(identities)):
        raise ValueError("DUPLICATE_QUALIFICATION_SUBJECT")
    return sorted(subjects, key=lambda subject: subject.subject_id)


def non_execution_authority(bindings: Mapping[str, Any]) -> dict[str, Any]:
    """Serialize supporting authority without claiming a new operation execution."""
    scope = min_q01_scope()
    declared = scope.get("non_execution_authority")
    if not isinstance(declared, Mapping):
        raise ValueError("INVALID_MIN_Q01_SCOPE")
    result: dict[str, Any] = {}
    for task_id, claims in declared.items():
        binding = bindings.get(task_id)
        if binding is None or not isinstance(claims, list):
            raise ValueError("MISSING_MIN_Q01_PREDECESSOR")
        result[task_id] = {
            "predecessor_binding": {
                "task_id": binding.task_id, "accepted_commit": binding.accepted_commit,
                "evidence_path": binding.evidence_path, "evidence_sha256": binding.evidence_sha256,
            },
            "claims": claims,
            "claim_scope": "immutable_accepted_authority",
        }
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "results/simulation/SIM-Q01_provenance_qualification.json")
    parser.add_argument("--report", type=Path, default=ROOT / "docs/simulation/SIM-Q01_provenance_qualification.md")
    args = parser.parse_args()
    bindings = {}
    for task_id, frozen_binding in FROZEN.items():
        acceptance = json.loads((ROOT / f"results/reviews/{task_id.removeprefix('TASK-')}_acceptance.json").read_text())
        bindings[task_id] = resolve_predecessor_binding(ROOT, task_id, acceptance, frozen_binding["evidence_path"], expected_binding=frozen_binding)
    subjects = collect_qualification_subjects(bindings, live_adapters())
    source_git_sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    evidence = aggregate_qualification_evidence(
        subjects, source_git_sha, required_subject_ids=set(required_subject_manifest(bindings)),
        required_subject_bindings={
            row["subject_id"]: {"task_id": row["predecessor_task_id"], "scenario_id": row["scenario_id"]}
            for row in min_q01_scope()["required_operation_subjects"]
        },
        immutable_authority=non_execution_authority(bindings),
    )
    write_qualification_artifacts(evidence, args.output, args.report)
    print(json.dumps(evidence, sort_keys=True))
    return 0 if evidence["task_specific_result"] == "SIM_PROVENANCE_QUALIFICATION_READY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
