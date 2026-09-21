"""Fail-closed accepted simulation evidence indexing and regression checks."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

SOURCE_TASKS = tuple(f"SIM-00{number}" for number in range(3, 10))
EXPECTED_RESULTS = {
    "SIM-003": "SIM_BASELINE_READY",
    "SIM-004": "SIM_NAVIGATION_BACKEND_READY",
    "SIM-005": "SIM_MANIPULATION_BACKEND_READY",
    "SIM-006": "SIM_VERIFICATION_BACKEND_READY",
    "SIM-007": "SIM_MISSION_INTEGRATION_BLOCKED",
    "SIM-008": "SIM_NORMAL_E2E_READY",
    "SIM-009": "SIM_FAILURE_SUITE_READY",
}
IDENTITY_FIELDS = ("mission_id", "request_id", "action_id", "trace_id")
CORRELATION_FIELDS = (*IDENTITY_FIELDS, "skill_result", "verification_result", "failure_code", "recovery_decision")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise ValueError("JSON root must be an object")
    return value


def _accepted(value: Mapping[str, Any]) -> bool:
    return value.get("status") == "ACCEPT" or value.get("review_decision") == "ACCEPT"


def _valid_hash(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(char in "0123456789abcdef" for char in value.lower())


def _source_hashes_valid(value: Any) -> bool:
    return isinstance(value, Mapping) and bool(value) and all(_valid_hash(item) for item in value.values())


def _profile_failures(profile: Any, provenance: Any) -> list[str]:
    if profile not in {"deterministic", "verification", "gazebo", "mujoco", "mixed"}:
        return ["MISSING_BACKEND_PROFILE"]
    if not isinstance(provenance, Mapping):
        return ["MISSING_SIMULATOR_PROVENANCE"]
    required: tuple[str, ...] = ()
    if profile == "gazebo":
        required = ("ros2_identity", "gazebo_version", "world_model_sha256", "bridge_sha256", "launch_sha256", "simulation_time", "wall_time_ms", "bounded_execution")
    elif profile == "mujoco":
        required = ("mujoco_version", "model_scene_config_sha256", "seed_identity", "timestep", "step_settings", "initial_state_identity")
    return [f"MISSING_{key.upper()}" for key in required if provenance.get(key) in (None, "", {}, [])]


def _correlation_failures(evidence: Mapping[str, Any]) -> list[str]:
    failures = [f"MISSING_{field.upper()}" for field in CORRELATION_FIELDS if field not in evidence]
    if any(evidence.get(field) in (None, "", [], {}) for field in IDENTITY_FIELDS):
        failures.append("INCOMPLETE_CORRELATION_IDENTITY")
    if evidence.get("failure_code") is None and evidence.get("recovery_decision") in (None, ""):
        failures.append("MISSING_RECOVERY_DECISION")
    return failures


def _scenario_failures(evidence: Mapping[str, Any]) -> list[str]:
    scenarios = evidence.get("scenarios")
    if not isinstance(scenarios, list) or not scenarios:
        return ["MISSING_SCENARIOS"]
    failures: list[str] = []
    for item in scenarios:
        if not isinstance(item, Mapping) or not isinstance(item.get("scenario_id"), str):
            failures.append("UNBOUND_SCENARIO")
            continue
        scenario_id = item["scenario_id"]
        if item.get("expected_outcome") != item.get("actual_outcome"):
            failures.append(f"SCENARIO_OUTCOME_MISMATCH:{scenario_id}")
        if item.get("lifecycle_expected") != item.get("lifecycle_actual"):
            failures.append(f"SCENARIO_LIFECYCLE_MISMATCH:{scenario_id}")
        if not isinstance(item.get("state_invariants"), Mapping) or not all(item["state_invariants"].values()):
            failures.append(f"SCENARIO_INVARIANT_FAILURE:{scenario_id}")
        for measurement in item.get("measurements", []):
            if not isinstance(measurement, Mapping) or abs(float(measurement.get("actual", 0)) - float(measurement.get("expected", 0))) > float(measurement.get("tolerance", -1)):
                failures.append(f"SCENARIO_TOLERANCE_FAILURE:{scenario_id}")
    return failures


def _deterministic_replay(evidences: list[Mapping[str, Any]]) -> dict[str, Any]:
    rows = [item for item in evidences if item.get("backend_profile") == "deterministic"]
    failures: list[str] = []
    for item in rows:
        replay = item.get("deterministic_replay")
        if not isinstance(replay, Mapping) or replay.get("expected_decision") != replay.get("actual_decision") or replay.get("expected_lifecycle") != replay.get("actual_lifecycle"):
            failures.append("DETERMINISTIC_REPLAY_MISMATCH")
    return {"status": "PASS" if rows and not failures else "BLOCKED", "criterion": "equivalent decisions and lifecycle outcomes", "failures": failures}


def _physics_semantic(evidences: list[Mapping[str, Any]]) -> dict[str, Any]:
    rows = [item for item in evidences if item.get("backend_profile") in {"gazebo", "mujoco", "mixed"}]
    failures = [failure for item in rows for failure in _scenario_failures(item)]
    profiles = {item.get("backend_profile") for item in rows}
    for profile in ("gazebo", "mujoco"):
        if profile not in profiles:
            failures.append(f"MISSING_REQUIRED_PHYSICS_PROFILE:{profile}")
    return {"status": "PASS" if rows and not failures else "BLOCKED", "criterion": "outcome, lifecycle, invariants, and declared tolerances", "failures": failures}


def build_regression_evidence(root: Path) -> dict[str, Any]:
    """Build a normalized, accepted-artifact-only regression record."""
    index: list[dict[str, Any]] = []
    valid_evidence: list[Mapping[str, Any]] = []
    for short_id in SOURCE_TASKS:
        acceptance_path = root / "results/reviews" / f"{short_id}_acceptance.json"
        row: dict[str, Any] = {"short_task_id": short_id, "acceptance_path": str(acceptance_path.relative_to(root)), "status": "PASS", "failures": []}
        try:
            acceptance = _load_json(acceptance_path)
            row["acceptance_sha256"] = sha256(acceptance_path)
            if acceptance.get("task_id") != f"TASK-{short_id}" or not _accepted(acceptance):
                row["failures"].append("INVALID_ACCEPTANCE")
            binding = acceptance.get("evidence")
            if not isinstance(binding, Mapping) or not isinstance(binding.get("path"), str) or not _valid_hash(binding.get("sha256")):
                row["failures"].append("MISSING_EVIDENCE_BINDING")
            else:
                evidence_path = root / binding["path"]
                row.update(evidence_path=binding["path"], expected_evidence_sha256=binding["sha256"])
                if not evidence_path.is_file():
                    row["failures"].append("MISSING_EVIDENCE")
                elif sha256(evidence_path) != binding["sha256"]:
                    row["failures"].append("EVIDENCE_HASH_MISMATCH")
                else:
                    evidence = _load_json(evidence_path)
                    row["evidence_sha256"] = sha256(evidence_path)
                    result, profile = evidence.get("task_specific_result"), evidence.get("backend_profile")
                    row["normalized_envelope"] = {"simulation_only": evidence.get("simulation_only") is True, "backend_profile": profile, "accepted_artifact_sha256": row["evidence_sha256"], "correlation": {field: evidence.get(field) for field in CORRELATION_FIELDS}, "result": result}
                    if evidence.get("task_id") != f"TASK-{short_id}": row["failures"].append("TASK_ID_MISMATCH")
                    if short_id in EXPECTED_RESULTS and result != EXPECTED_RESULTS[short_id]: row["failures"].append("UNEXPECTED_TASK_RESULT")
                    if evidence.get("simulation_only") is not True: row["failures"].append("MISSING_SIMULATION_ONLY_LABEL")
                    if not _source_hashes_valid(evidence.get("source_hashes")): row["failures"].append("MISSING_SOURCE_CONFIG_HASHES")
                    row["failures"].extend(_correlation_failures(evidence))
                    row["failures"].extend(_profile_failures(profile, evidence.get("simulator_provenance")))
                    row["failures"].extend(_scenario_failures(evidence))
                    if not row["failures"]: valid_evidence.append(evidence)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            row["failures"].append(f"UNREADABLE_SOURCE:{type(exc).__name__}")
        if row["failures"]: row["status"] = "FAIL"
        index.append(row)
    deterministic, physics = _deterministic_replay(valid_evidence), _physics_semantic(valid_evidence)
    normal = next((row for row in index if row["short_task_id"] == "SIM-008"), None)
    failure = next((row for row in index if row["short_task_id"] == "SIM-009"), None)
    coverage_failures = [] if normal and failure and normal["status"] == failure["status"] == "PASS" else ["UNBOUND_NORMAL_OR_FAILURE_SUITE"]
    ready = all(row["status"] == "PASS" for row in index) and not coverage_failures and deterministic["status"] == physics["status"] == "PASS"
    return {"schema_version": "1.0", "task_id": "TASK-SIM-010", "simulation_only": True, "claim_scope": "Simulation evidence only; no physical or production performance claim.", "accepted_source_index": index, "deterministic_replay": deterministic, "physics_semantic_regression": physics, "normal_failure_suite_coverage": {"status": "PASS" if not coverage_failures else "BLOCKED", "failures": coverage_failures}, "task_specific_result": "SIM_OBSERVABILITY_REGRESSION_READY" if ready else "SIM_OBSERVABILITY_REGRESSION_BLOCKED"}
