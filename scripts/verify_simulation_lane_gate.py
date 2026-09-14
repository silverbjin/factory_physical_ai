#!/usr/bin/env python3
"""Reconstruct the TASK-SIM-GATE decision from accepted repository evidence.

The verifier is intentionally read-only except for its explicitly requested JSON
output.  It never executes the smoke runtime and never grants physical, Week,
Dataset V1, training, or hardware-selection authority.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
import subprocess
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
TASK_ID = "TASK-SIM-GATE"
SCHEMA_VERSION = "1.0"
SIM_GO = "SIM_GO"
SIM_NO_GO = "SIM_NO_GO"

REQUIRED_CONTEXT_PATHS = (
    "docs/architecture/adr/ADR-Simulation-Lane-v1.md",
    "context/simulation_task_mapping_v1.md",
    "docs/architecture/system_architecture_v1.md",
    "docs/contracts/contract_plan.md",
    "docs/hardware/hardware_target_selection_status_v1.md",
    "results/phase0/P0-004R_vla_readiness.json",
    "docs/simulation/simulation_contract_profile_v1.md",
    "results/simulation/SIM-001_contract_profile.json",
    "results/reviews/SIM-001_acceptance.json",
    "docs/simulation/simulation_smoke_runtime_v1.md",
    "results/simulation/SIM-002_smoke_runtime.json",
    "results/reviews/SIM-002_acceptance.json",
)

EXPECTED_OPERATIONS = {
    "mission.execute",
    "navigation.execute",
    "vla.execute",
    "action_status.get",
    "verification.verify",
}
EXPECTED_BOUNDARIES = {
    "mission_executor",
    "navigation_skill",
    "vla_skill",
    "verification",
}
EXPECTED_SIM_001_SOURCE_PATHS = {
    "docs/architecture/adr/ADR-Simulation-Lane-v1.md",
    "context/simulation_task_mapping_v1.md",
    "docs/architecture/system_architecture_v1.md",
    "docs/contracts/contract_plan.md",
    "docs/contracts/simulation_execution_contract_v1.md",
    "docs/contracts/schemas/simulation_execution_contract_v1.schema.json",
    "results/reviews/SIM-C01_acceptance.json",
    "docs/hardware/hardware_target_selection_status_v1.md",
    "docs/architecture/adr/ADR-001-manipulator.md",
    "docs/architecture/adr/ADR-002-amr.md",
    "docs/architecture/adr/ADR-005-camera-observation.md",
    "docs/architecture/adr/ADR-010-deployment-topology.md",
    "results/phase0/P0-004R_vla_readiness.json",
}
EXPECTED_SIM_002_SOURCE_PATHS = {
    "docs/architecture/adr/ADR-Simulation-Lane-v1.md",
    "context/simulation_task_mapping_v1.md",
    "docs/architecture/system_architecture_v1.md",
    "docs/contracts/contract_plan.md",
    "results/phase0/P0-004R_vla_readiness.json",
    "docs/simulation/simulation_contract_profile_v1.md",
    "results/simulation/SIM-001_contract_profile.json",
    "results/reviews/SIM-001_acceptance.json",
}


def canonical_payload_sha256(document: Mapping[str, Any]) -> str:
    """Hash a JSON object after excluding its self-referential payload hash."""

    payload = deepcopy(dict(document))
    payload.pop("payload_sha256", None)
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _sha256(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except (OSError, ValueError):
        return None


def _load_json(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _dig(value: object, *keys: str, default: Any = None) -> Any:
    current = value
    for key in keys:
        if not isinstance(current, Mapping) or key not in current:
            return default
        current = current[key]
    return current


def _file_binding_matches(
    root: Path,
    record: Mapping[str, Any] | None,
    path_key: str,
    sha_key: str,
) -> bool:
    if not isinstance(record, Mapping):
        return False
    relative = record.get(path_key)
    expected = record.get(sha_key)
    if not isinstance(relative, str) or not isinstance(expected, str):
        return False
    return _sha256(root / relative) == expected


def _source_bindings_match(
    root: Path,
    evidence: Mapping[str, Any] | None,
    expected_paths: set[str],
) -> bool:
    bindings = _dig(evidence, "source_bindings")
    if not isinstance(bindings, list) or not bindings:
        return False
    seen: set[str] = set()
    for binding in bindings:
        if not isinstance(binding, Mapping):
            return False
        relative = binding.get("path")
        expected = binding.get("sha256")
        if not isinstance(relative, str) or not isinstance(expected, str) or relative in seen:
            return False
        seen.add(relative)
        if _sha256(root / relative) != expected:
            return False
    return seen == expected_paths


def _payload_matches(evidence: Mapping[str, Any] | None) -> bool:
    if not isinstance(evidence, Mapping):
        return False
    claimed = evidence.get("payload_sha256")
    return isinstance(claimed, str) and canonical_payload_sha256(evidence) == claimed


def _commit_exists(git_root: Path, commit: object) -> bool:
    if not isinstance(commit, str) or len(commit) != 40:
        return False
    try:
        completed = subprocess.run(
            ["git", "cat-file", "-e", f"{commit}^{{commit}}"],
            cwd=git_root,
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return completed.returncode == 0


def _git_blob_sha256(git_root: Path, commit: object, relative: object) -> str | None:
    """Return the exact reviewed Git blob hash, rejecting ambiguous paths."""

    if not isinstance(commit, str) or len(commit) != 40 or not isinstance(relative, str):
        return None
    path = Path(relative)
    if path.is_absolute() or not path.parts or any(part in {"", ".", ".."} for part in path.parts):
        return None
    try:
        completed = subprocess.run(
            ["git", "show", f"{commit}:{relative}"],
            cwd=git_root,
            check=False,
            capture_output=True,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if completed.returncode != 0:
        return None
    return hashlib.sha256(completed.stdout).hexdigest()


def _reviewed_file_binding_matches(
    root: Path,
    git_root: Path,
    record: Mapping[str, Any] | None,
    path_key: str,
    sha_key: str,
) -> bool:
    """Bind an accepted current file to the exact independently reviewed blob."""

    if not _file_binding_matches(root, record, path_key, sha_key):
        return False
    relative = _dig(record, path_key)
    expected = _dig(record, sha_key)
    reviewed_commit = _dig(record, "reviewed_commit")
    return _git_blob_sha256(git_root, reviewed_commit, relative) == expected


def _runtime_operations_are_allowlisted(runtime_text: str) -> bool:
    """Reject operation-like identifiers outside the frozen logical operations."""

    try:
        tree = ast.parse(runtime_text)
    except (SyntaxError, ValueError):
        return False
    operation_pattern = re.compile(r"^[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)+$")
    operations = {
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and operation_pattern.fullmatch(node.value)
    }
    return bool(operations) and operations == EXPECTED_OPERATIONS


def _conservative_bool(value: object) -> bool:
    """Preserve authoritative booleans and fail closed for every other type."""

    return value if isinstance(value, bool) else False


def _review_record_matches(
    root: Path,
    acceptance: Mapping[str, Any] | None,
    *,
    task_decision: str,
) -> bool:
    if not _file_binding_matches(root, acceptance, "review_record_path", "review_record_sha256"):
        return False
    relative = _dig(acceptance, "review_record_path")
    try:
        text = (root / relative).read_text(encoding="utf-8")
    except (OSError, UnicodeError, TypeError):
        return False
    return (
        "Recommendation: `ACCEPT`" in text
        and task_decision in text
    )


def _required_context_bindings(root: Path) -> list[dict[str, Any]]:
    return [
        {
            "path": relative,
            "exists": (root / relative).is_file(),
            "sha256": _sha256(root / relative),
        }
        for relative in REQUIRED_CONTEXT_PATHS
    ]


def _check(
    checks: dict[str, dict[str, Any]],
    check_id: str,
    name: str,
    passed: bool,
    detail: str,
) -> None:
    checks[check_id] = {
        "name": name,
        "status": "PASS" if passed else "FAIL",
        "detail": detail,
    }


def _scenario_map(sim_002: Mapping[str, Any] | None) -> dict[str, Mapping[str, Any]]:
    scenarios = _dig(sim_002, "scenario_results")
    if not isinstance(scenarios, list):
        return {}
    result: dict[str, Mapping[str, Any]] = {}
    for item in scenarios:
        if isinstance(item, Mapping) and isinstance(item.get("scenario_id"), str):
            result[str(item["scenario_id"])] = item
    return result


def _bounded_smoke_is_valid(sim_002: Mapping[str, Any] | None) -> bool:
    scenarios = _scenario_map(sim_002)
    if set(scenarios) != {"S01", "S02", "S03", "S04"}:
        return False
    bounds = [item.get("execution_bound_ms") for item in scenarios.values()]
    if not all(isinstance(value, int) and not isinstance(value, bool) and value > 0 for value in bounds):
        return False
    boundedness = _dig(sim_002, "boundedness", default={})
    cleanup = _dig(sim_002, "process_cleanup", default={})
    return all(
        (
            _dig(sim_002, "decision") == "SIM_SMOKE_READY",
            _dig(boundedness, "all_scenarios_bounded") is True,
            _dig(boundedness, "unbounded_waits") is False,
            _dig(boundedness, "retries_performed") == 0,
            _dig(cleanup, "child_processes_started") == 0,
            _dig(cleanup, "background_workers_started") == 0,
            _dig(cleanup, "temporary_files_created") == 0,
            _dig(cleanup, "cleanup_complete") is True,
            _dig(scenarios["S01"], "final_mission_status") == "completed",
            _dig(scenarios["S01"], "verification_verdict") == "pass",
            _dig(scenarios["S02"], "observed_status") == "failed",
            _dig(scenarios["S02"], "observed_result") == "failure",
            _dig(scenarios["S03"], "observed_status") == "unknown",
            _dig(scenarios["S03"], "observed_result") == "pending",
            _dig(scenarios["S04"], "state_sequence") == ["unknown", "reconciling", "reconciled"],
            _dig(scenarios["S04"], "direct_unknown_to_succeeded") is False,
            _dig(scenarios["S04"], "authoritative_evidence_required") is True,
        )
    )


def evaluate_simulation_lane_gate(
    root: Path = ROOT,
    *,
    git_root: Path | None = None,
    generation_timestamp: str | None = None,
    generation_git_head: str | None = None,
    pre_implementation_clean: bool | None = None,
) -> dict[str, Any]:
    """Evaluate all material predicates and return a fail-closed gate record."""

    root = root.resolve()
    git_root = (git_root or root).resolve()
    context_bindings = _required_context_bindings(root)

    adr_path = root / REQUIRED_CONTEXT_PATHS[0]
    mapping_path = root / REQUIRED_CONTEXT_PATHS[1]
    hardware_path = root / REQUIRED_CONTEXT_PATHS[4]
    p0_path = root / REQUIRED_CONTEXT_PATHS[5]
    sim_001_profile_path = root / REQUIRED_CONTEXT_PATHS[6]
    sim_001_evidence_path = root / REQUIRED_CONTEXT_PATHS[7]
    sim_001_acceptance_path = root / REQUIRED_CONTEXT_PATHS[8]
    sim_002_report_path = root / REQUIRED_CONTEXT_PATHS[9]
    sim_002_evidence_path = root / REQUIRED_CONTEXT_PATHS[10]
    sim_002_acceptance_path = root / REQUIRED_CONTEXT_PATHS[11]

    sim_001 = _load_json(sim_001_evidence_path)
    sim_001_acceptance = _load_json(sim_001_acceptance_path)
    sim_002 = _load_json(sim_002_evidence_path)
    sim_002_acceptance = _load_json(sim_002_acceptance_path)
    p0 = _load_json(p0_path)

    adr_text = adr_path.read_text(encoding="utf-8") if adr_path.is_file() else ""
    mapping_text = mapping_path.read_text(encoding="utf-8") if mapping_path.is_file() else ""
    hardware_text = hardware_path.read_text(encoding="utf-8") if hardware_path.is_file() else ""

    sim_001_acceptance_sha = _sha256(sim_001_acceptance_path)
    sim_002_acceptance_sha = _sha256(sim_002_acceptance_path)

    sim_001_identity = (
        _dig(sim_001_acceptance, "task_id") == "TASK-SIM-001"
        and _dig(sim_001_acceptance, "review_decision") == "ACCEPT"
        and _review_record_matches(
            root,
            sim_001_acceptance,
            task_decision="SIM_CONTRACT_PROFILE_READY",
        )
        and _commit_exists(git_root, _dig(sim_001_acceptance, "reviewed_commit"))
    )
    sim_001_ready = (
        _dig(sim_001_acceptance, "task_specific_decision") == "SIM_CONTRACT_PROFILE_READY"
        and _dig(sim_001, "task_id") == "TASK-SIM-001"
        and _dig(sim_001, "decision") == "SIM_CONTRACT_PROFILE_READY"
        and _dig(sim_001, "unresolved_contract_gaps") == []
    )
    sim_001_immutable = all(
        (
            _reviewed_file_binding_matches(
                root, git_root, sim_001_acceptance, "profile_path", "profile_sha256"
            ),
            _reviewed_file_binding_matches(
                root, git_root, sim_001_acceptance, "evidence_path", "evidence_sha256"
            ),
            _payload_matches(sim_001),
            _dig(sim_001_acceptance, "accepted_payload_sha256") == _dig(sim_001, "payload_sha256"),
            _source_bindings_match(root, sim_001, EXPECTED_SIM_001_SOURCE_PATHS),
            _dig(sim_001, "profile", "sha256") == _sha256(sim_001_profile_path),
            _file_binding_matches(
                root,
                sim_001_acceptance,
                "simulation_execution_contract_path",
                "simulation_execution_contract_sha256",
            ),
            _file_binding_matches(
                root,
                sim_001_acceptance,
                "simulation_execution_schema_path",
                "simulation_execution_schema_sha256",
            ),
            _file_binding_matches(root, sim_001_acceptance, "contract_plan_path", "contract_plan_sha256"),
            _file_binding_matches(root, sim_001_acceptance, "sim_c01_acceptance_path", "sim_c01_acceptance_sha256"),
        )
    )

    sim_002_identity = (
        _dig(sim_002_acceptance, "task_id") == "TASK-SIM-002"
        and _dig(sim_002_acceptance, "review_decision") == "ACCEPT"
        and _review_record_matches(root, sim_002_acceptance, task_decision="SIM_SMOKE_READY")
        and _commit_exists(git_root, _dig(sim_002_acceptance, "reviewed_commit"))
    )
    sim_002_ready = (
        _dig(sim_002_acceptance, "task_specific_decision") == "SIM_SMOKE_READY"
        and _dig(sim_002, "task_id") == "TASK-SIM-002"
        and _dig(sim_002, "decision") == "SIM_SMOKE_READY"
    )
    sim_002_immutable = all(
        (
            _reviewed_file_binding_matches(
                root, git_root, sim_002_acceptance, "evidence_path", "evidence_sha256"
            ),
            _reviewed_file_binding_matches(
                root, git_root, sim_002_acceptance, "smoke_report_path", "smoke_report_sha256"
            ),
            _reviewed_file_binding_matches(
                root, git_root, sim_002_acceptance, "smoke_entry_point_path", "smoke_entry_point_sha256"
            ),
            _reviewed_file_binding_matches(
                root, git_root, sim_002_acceptance, "runtime_module_path", "runtime_module_sha256"
            ),
            _reviewed_file_binding_matches(
                root, git_root, sim_002_acceptance, "focused_test_path", "focused_test_sha256"
            ),
            _payload_matches(sim_002),
            _dig(sim_002_acceptance, "evidence_payload_sha256") == _dig(sim_002, "payload_sha256"),
            _source_bindings_match(root, sim_002, EXPECTED_SIM_002_SOURCE_PATHS),
            _dig(sim_002, "smoke_report", "sha256") == _sha256(sim_002_report_path),
        )
    )
    sim_002_to_sim_001 = all(
        (
            isinstance(sim_001_acceptance_sha, str),
            _dig(sim_002, "sim_001_binding", "acceptance_sha256") == sim_001_acceptance_sha,
            _dig(sim_002_acceptance, "sim_001_acceptance_sha256") == sim_001_acceptance_sha,
            _dig(sim_002, "sim_001_binding", "evidence_sha256") == _sha256(sim_001_evidence_path),
            _dig(sim_002, "sim_001_binding", "profile_sha256") == _sha256(sim_001_profile_path),
            _dig(sim_002, "sim_001_binding", "reviewed_commit") == _dig(sim_001_acceptance, "reviewed_commit"),
            _dig(sim_002, "sim_001_binding", "review_decision") == "ACCEPT",
            _dig(sim_002, "sim_001_binding", "task_specific_decision") == "SIM_CONTRACT_PROFILE_READY",
        )
    )

    p0_authorization = _dig(p0, "authorization", default={})
    p0_valid = (
        _dig(p0, "task") == "TASK-P0-004R"
        and _dig(p0, "final_gate") == "NO_GO"
        and all(
            isinstance(_dig(p0_authorization, key), bool)
            for key in (
                "task_w1_001",
                "task_w1_002",
                "dataset_v1",
                "smolvla_fine_tuning",
                "physical_motion",
            )
        )
        and _dig(sim_001, "p0_004r_authorization", "sha256") == _sha256(p0_path)
        and _dig(sim_002_acceptance, "p0_004r_authorization_sha256") == _sha256(p0_path)
    )
    week_preserved = p0_valid and all(
        (
            _dig(sim_001, "final_authorization_snapshot", "task_w1_001_authorized")
            == _dig(p0_authorization, "task_w1_001"),
            _dig(sim_001, "final_authorization_snapshot", "task_w1_002_authorized")
            == _dig(p0_authorization, "task_w1_002"),
            _dig(sim_002, "authorization_snapshot", "task_w1_001_authorized")
            == _dig(p0_authorization, "task_w1_001"),
            _dig(sim_002, "authorization_snapshot", "task_w1_002_authorized")
            == _dig(p0_authorization, "task_w1_002"),
            _dig(sim_002, "week_authorization_modified") is False,
        )
    )
    dataset_boundary = all(
        (
            _dig(sim_001, "fixture_profile", "identifier") == "SIM_FIXTURE_SET_V1",
            _dig(sim_001, "fixture_profile", "dataset_v1_equivalent") is False,
            _dig(sim_002, "dataset_v1_created") is False,
            _dig(sim_002, "authorization_snapshot", "dataset_v1_authorized")
            == _dig(p0_authorization, "dataset_v1"),
            _dig(sim_002, "authorization_snapshot", "dataset_v1_authorized") is False,
        )
    )
    training_boundary = all(
        (
            _dig(sim_001, "training_required") is False,
            _dig(sim_002, "training_dependency") is False,
            _dig(sim_002, "authorization_snapshot", "smolvla_fine_tuning_authorized")
            == _dig(p0_authorization, "smolvla_fine_tuning"),
            _dig(p0_authorization, "smolvla_fine_tuning") is False,
        )
    )
    physical_independence = all(
        (
            _dig(sim_001, "physical_dependency_required") is False,
            _dig(sim_002, "physical_dependency") is False,
            _dig(sim_002_acceptance, "downstream_authorization", "physical_robot_execution_authorized") is False,
        )
    )
    camera_independence = all(
        (
            _dig(sim_002, "physical_camera_dependency") is False,
            _dig(sim_002_acceptance, "downstream_authorization", "physical_camera_execution_authorized") is False,
        )
    )
    no_physical_motion = all(
        (
            _dig(sim_002, "physical_motion_executed") is False,
            _dig(sim_002, "authorization_snapshot", "physical_motion_authorized")
            == _dig(p0_authorization, "physical_motion"),
            _dig(p0_authorization, "physical_motion") is False,
            _dig(sim_002_acceptance, "downstream_authorization", "physical_robot_execution_authorized") is False,
        )
    )

    classifications = _dig(sim_001, "boundary_classification", default={})
    operations = _dig(sim_001, "executable_contract_status", "logical_operations", default=[])
    contract_boundary = (
        isinstance(classifications, Mapping)
        and set(classifications) == EXPECTED_BOUNDARIES
        and all(value == "EXECUTABLE_CONTRACT_AVAILABLE" for value in classifications.values())
        and isinstance(operations, list)
        and set(operations) == EXPECTED_OPERATIONS
    )
    runtime_relative = _dig(sim_002_acceptance, "runtime_module_path")
    try:
        runtime_text = (root / runtime_relative).read_text(encoding="utf-8")
    except (OSError, UnicodeError, TypeError):
        runtime_text = ""
    prohibited_runtime_tokens = {
        "ManipulatorPort",
        "NavigationPort",
        "ObservationPort",
        "joint_command",
        "motor_command",
        "gripper_command",
        "trajectory_command",
        "/dev/tty",
        "/dev/video",
    }
    no_direct_actuator = (
        _dig(sim_001, "direct_actuator_contract_introduced") is False
        and contract_boundary
        and bool(runtime_text)
        and _runtime_operations_are_allowlisted(runtime_text)
        and not any(token in runtime_text for token in prohibited_runtime_tokens)
    )
    hardware_not_frozen = (
        "INFORMATIONAL / NOT FROZEN" in hardware_text
        and "This document is not a hardware freeze." in hardware_text
        and _dig(sim_002, "authorization_snapshot", "hardware_target_frozen") is False
        and _dig(sim_002_acceptance, "downstream_authorization", "hardware_target_frozen") is False
    )

    checks: dict[str, dict[str, Any]] = {}
    source_bindings_valid = _source_bindings_match(
        root, sim_001, EXPECTED_SIM_001_SOURCE_PATHS
    ) and _source_bindings_match(root, sim_002, EXPECTED_SIM_002_SOURCE_PATHS)
    definitions = (
        (
            "C01",
            "Governing ADR",
            "Status: FROZEN" in adr_text and source_bindings_valid,
            "FROZEN ADR and predecessor source bindings must match.",
        ),
        (
            "C02",
            "Simulation Mapping",
            "Status: FROZEN" in mapping_text
            and "TASK-SIM-001 precedes TASK-SIM-002" in mapping_text
            and "TASK-SIM-002 precedes TASK-SIM-GATE" in mapping_text
            and source_bindings_valid,
            "Frozen acyclic ordering and hashes must match.",
        ),
        (
            "C03",
            "SIM-001 Independent Acceptance",
            sim_001_identity,
            "Independent acceptance, review record, and reviewed commit are reconstructed.",
        ),
        (
            "C04",
            "SIM-001 READY State",
            sim_001_ready,
            "Acceptance and canonical evidence must both state SIM_CONTRACT_PROFILE_READY.",
        ),
        (
            "C05",
            "SIM-001 Immutable Binding",
            sim_001_immutable,
            "Profile, evidence, payload, source, contract, schema, and C01 bindings must match.",
        ),
        (
            "C06",
            "SIM-002 Independent Acceptance",
            sim_002_identity,
            "Independent acceptance, review record, and reviewed commit are reconstructed.",
        ),
        (
            "C07",
            "SIM-002 READY State",
            sim_002_ready,
            "Acceptance and canonical evidence must both state SIM_SMOKE_READY.",
        ),
        (
            "C08",
            "SIM-002 Immutable Binding",
            sim_002_immutable,
            "Evidence, report, payload, code, test, and source bindings must match.",
        ),
        (
            "C09",
            "SIM-002 to SIM-001 Binding",
            sim_002_to_sim_001,
            "SIM-002 must bind the current accepted SIM-001 revision.",
        ),
        (
            "C10",
            "Bounded Smoke Execution",
            _bounded_smoke_is_valid(sim_002),
            "Four semantic scenarios and cleanup must be finite and valid.",
        ),
        (
            "C11",
            "Physical Independence",
            physical_independence,
            "No physical robot dependency or authorization is allowed.",
        ),
        (
            "C12",
            "Camera Independence",
            camera_independence,
            "No physical camera dependency or authorization is allowed.",
        ),
        (
            "C13",
            "No Physical Motion",
            no_physical_motion,
            "No physical motion may be executed or authorized.",
        ),
        (
            "C14",
            "No Week Authorization Rewrite",
            week_preserved,
            "Week booleans must match P0-004R exactly.",
        ),
        (
            "C15",
            "Dataset Boundary",
            dataset_boundary,
            "SIM_FIXTURE_SET_V1 must remain distinct from unauthorized Dataset V1.",
        ),
        (
            "C16",
            "Training Boundary",
            training_boundary,
            "Simulation must not require or authorize fine-tuning.",
        ),
        (
            "C17",
            "Contract Boundary",
            contract_boundary,
            "Only accepted executor/skill/verification logical operations are allowed.",
        ),
        (
            "C18",
            "No Direct Actuator Contract",
            bool(no_direct_actuator),
            "No direct actuator ownership or lower-level public port is allowed.",
        ),
        (
            "C19",
            "Historical P0 Evidence Preserved",
            p0_valid and hardware_not_frozen,
            "P0-004R must remain NO_GO and hardware informational/not frozen.",
        ),
    )
    for check_id, name, passed, detail in definitions:
        _check(checks, check_id, name, passed, detail)

    material_before_c20 = all(item["status"] == "PASS" for item in checks.values())
    _check(
        checks,
        "C20",
        "Decision Reconstruction",
        material_before_c20,
        "Result is derived from C01-C19, not a self-reported PASS or SIM_GO field.",
    )

    all_pass = all(item["status"] == "PASS" for item in checks.values())
    gate_result = SIM_GO if all_pass else SIM_NO_GO
    unresolved = [
        {"check_id": check_id, "name": item["name"], "detail": item["detail"]}
        for check_id, item in checks.items()
        if item["status"] != "PASS"
    ]

    if generation_timestamp is None:
        generation_timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    if generation_git_head is None:
        try:
            generation_git_head = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=git_root,
                check=True,
                capture_output=True,
                text=True,
                timeout=5,
            ).stdout.strip()
        except (OSError, subprocess.SubprocessError):
            generation_git_head = "UNKNOWN"

    authorization_snapshot = {
        "simulation_lane_authorized": False,
        "task_w1_001_authorized": _conservative_bool(_dig(p0_authorization, "task_w1_001")),
        "task_w1_002_authorized": _conservative_bool(_dig(p0_authorization, "task_w1_002")),
        "dataset_v1_authorized": _conservative_bool(_dig(p0_authorization, "dataset_v1")),
        "fine_tuning_authorized": _conservative_bool(
            _dig(p0_authorization, "smolvla_fine_tuning")
        ),
        "physical_motion_authorized": _conservative_bool(
            _dig(p0_authorization, "physical_motion")
        ),
        "physical_gripper_authorized": False,
        "physical_teleop_authorized": False,
        "physical_dataset_collection_authorized": False,
        "hardware_target_frozen": False,
    }
    evidence: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "task_id": TASK_ID,
        "implementation_complete": True,
        "gate_result": gate_result,
        "generation_timestamp": generation_timestamp,
        "generation_git_head": generation_git_head,
        "worktree_state": {
            "pre_implementation_clean": pre_implementation_clean,
            "at_generation": "DIRTY",
            "staged_changes": False,
            "commit_performed": False,
        },
        "required_context_bindings": context_bindings,
        "sim_001": {
            "evidence_path": "results/simulation/SIM-001_contract_profile.json",
            "evidence_sha256": _sha256(sim_001_evidence_path),
            "profile_path": "docs/simulation/simulation_contract_profile_v1.md",
            "profile_sha256": _sha256(sim_001_profile_path),
            "acceptance_path": "results/reviews/SIM-001_acceptance.json",
            "acceptance_sha256": sim_001_acceptance_sha,
            "review_decision": _dig(sim_001_acceptance, "review_decision"),
            "task_specific_decision": _dig(sim_001_acceptance, "task_specific_decision"),
            "reviewed_commit": _dig(sim_001_acceptance, "reviewed_commit"),
        },
        "sim_002": {
            "evidence_path": "results/simulation/SIM-002_smoke_runtime.json",
            "evidence_sha256": _sha256(sim_002_evidence_path),
            "report_path": "docs/simulation/simulation_smoke_runtime_v1.md",
            "report_sha256": _sha256(sim_002_report_path),
            "acceptance_path": "results/reviews/SIM-002_acceptance.json",
            "acceptance_sha256": sim_002_acceptance_sha,
            "review_decision": _dig(sim_002_acceptance, "review_decision"),
            "task_specific_decision": _dig(sim_002_acceptance, "task_specific_decision"),
            "reviewed_commit": _dig(sim_002_acceptance, "reviewed_commit"),
            "bound_sim_001_acceptance_sha256": _dig(sim_002, "sim_001_binding", "acceptance_sha256"),
        },
        "p0_004r": {
            "path": "results/phase0/P0-004R_vla_readiness.json",
            "sha256": _sha256(p0_path),
            "final_gate": _dig(p0, "final_gate"),
        },
        "implementation_artifacts": {
            "verifier_path": "scripts/verify_simulation_lane_gate.py",
            "verifier_sha256": _sha256(root / "scripts/verify_simulation_lane_gate.py"),
            "focused_test_path": "tests/test_simulation_lane_gate.py",
            "focused_test_sha256": _sha256(root / "tests/test_simulation_lane_gate.py"),
            "report_path": "docs/simulation/simulation_lane_gate_v1.md",
            "report_sha256": _sha256(root / "docs/simulation/simulation_lane_gate_v1.md"),
        },
        "authorization_snapshot": authorization_snapshot,
        "material_predicates": checks,
        "unresolved_blockers": unresolved,
        "independent_acceptance": "PENDING",
        "simulation_lane_authorization_effective": False,
        "payload_hash_algorithm": (
            "sha256(canonical JSON with sorted keys and compact separators, "
            "excluding payload_sha256)"
        ),
    }
    evidence["payload_sha256"] = canonical_payload_sha256(evidence)
    return evidence


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "results/simulation/SIM-GATE_readiness.json",
        help="Path for the reconstructed gate evidence.",
    )
    args = parser.parse_args()
    evidence = evaluate_simulation_lane_gate(ROOT, pre_implementation_clean=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(evidence, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(evidence, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
