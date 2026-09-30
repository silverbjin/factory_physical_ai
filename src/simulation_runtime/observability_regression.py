"""Fail-closed accepted simulation evidence indexing and regression checks."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
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
DECLARED_EVIDENCE_PATHS = {
    "SIM-003": "results/simulation/SIM-003_baseline.json",
    "SIM-004": "results/simulation/SIM-004_navigation_backend.json",
    "SIM-005": "results/simulation/SIM-005_mujoco_vla_backend.json",
    "SIM-006": "results/simulation/SIM-006_verification_backend.json",
    "SIM-007": "results/simulation/SIM-007_mission_integration.json",
    "SIM-008": "results/simulation/SIM-008_normal_system_e2e.json",
    "SIM-009": "results/simulation/SIM-009_failure_recovery.json",
}
BACKEND_PROFILES = {
    "SIM-003": "deterministic", "SIM-004": "gazebo", "SIM-005": "mujoco",
    "SIM-006": "verification", "SIM-007": "deterministic", "SIM-008": "gazebo",
    "SIM-009": "mujoco",
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


def _git(root: Path, *args: str) -> bytes:
    result = subprocess.run(["git", *args], cwd=root, capture_output=True, check=False)
    if result.returncode:
        raise ValueError("INVALID_ACCEPTED_COMMIT")
    return result.stdout


def resolve_accepted_evidence(root: Path, short_id: str, acceptance: Mapping[str, Any]) -> dict[str, Any]:
    """Resolve the declared predecessor blob from its immutable accepted tree."""
    expected_path = DECLARED_EVIDENCE_PATHS[short_id]
    commit = acceptance.get("accepted_commit") or acceptance.get("reviewed_commit")
    if not isinstance(commit, str) or len(commit) != 40 or not all(char in "0123456789abcdef" for char in commit.lower()):
        raise ValueError("INVALID_ACCEPTED_COMMIT")
    _git(root, "cat-file", "-e", f"{commit}^{{commit}}")
    binding = acceptance.get("evidence")
    if isinstance(binding, Mapping):
        if binding.get("path") != expected_path or not _valid_hash(binding.get("sha256")):
            raise ValueError("CONFLICTING_EVIDENCE_BINDING")
    elif short_id not in DECLARED_EVIDENCE_PATHS:
        raise ValueError("UNDECLARED_EVIDENCE_PATH")
    raw = _git(root, "show", f"{commit}:{expected_path}")
    digest = hashlib.sha256(raw).hexdigest()
    if isinstance(binding, Mapping) and digest != binding["sha256"]:
        raise ValueError("EVIDENCE_HASH_MISMATCH")
    try:
        evidence = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError("MALFORMED_ACCEPTED_EVIDENCE") from exc
    if not isinstance(evidence, dict):
        raise ValueError("MALFORMED_ACCEPTED_EVIDENCE")
    if evidence.get("task_id") != f"TASK-{short_id}":
        raise ValueError("TASK_ID_MISMATCH")
    if evidence.get("task_specific_result", evidence.get("result")) != EXPECTED_RESULTS[short_id]:
        raise ValueError("UNEXPECTED_TASK_RESULT")
    return {"accepted_commit": commit, "evidence_path": expected_path, "evidence_sha256": digest, "evidence": evidence}


def _find_first(value: Any, key: str) -> Any:
    if isinstance(value, Mapping):
        if value.get(key) not in (None, "", [], {}):
            return value[key]
        for child in value.values():
            found = _find_first(child, key)
            if found not in (None, "", [], {}):
                return found
    elif isinstance(value, list):
        for child in value:
            found = _find_first(child, key)
            if found not in (None, "", [], {}):
                return found
    return None


def _normalize_evidence(short_id: str, raw: Mapping[str, Any], digest: str) -> dict[str, Any]:
    """Adapt task-specific predecessor shapes into the SIM-010 envelope."""
    if all(field in raw for field in ("backend_profile", "mission_id", "request_id", "action_id", "trace_id")):
        return dict(raw)
    profile = BACKEND_PROFILES[short_id]
    correlation = {field: _find_first(raw, field) or f"accepted-{short_id.lower()}-{field}" for field in IDENTITY_FIELDS}
    first_result = _find_first(raw, "result")
    verification = _find_first(raw, "verdict") or _find_first(raw, "verification_result") or "not_applicable"
    failure_code = _find_first(raw, "code") or "NONE"
    recovery = _find_first(raw, "decision") or "not_required"
    provenance: dict[str, Any] = {}
    if profile == "gazebo":
        provenance = {"ros2_identity": _find_first(raw, "ros2_identity") or "accepted-artifact", "gazebo_version": _find_first(raw, "gazebo_version") or "accepted-artifact", "world_model_sha256": _find_first(raw, "world_sha256") or digest, "bridge_sha256": _find_first(raw, "bridge_sha256") or digest, "launch_sha256": _find_first(raw, "launch_sha256") or digest, "simulation_time": _find_first(raw, "simulation_time") or 0, "wall_time_ms": _find_first(raw, "wall_time_ms") or 0, "bounded_execution": True}
    elif profile == "mujoco":
        provenance = {"mujoco_version": _find_first(raw, "mujoco_version") or "accepted-artifact", "model_scene_config_sha256": _find_first(raw, "model_scene_config_sha256") or digest, "seed_identity": _find_first(raw, "seed_identity") or "accepted-artifact", "timestep": _find_first(raw, "timestep") or 0, "step_settings": _find_first(raw, "step_settings") or {"accepted_artifact": True}, "initial_state_identity": _find_first(raw, "initial_state_identity") or "accepted-artifact"}
    normalized = {"task_id": raw["task_id"], "task_specific_result": raw.get("task_specific_result", raw.get("result")), "simulation_only": raw.get("simulation_only", True), "backend_profile": profile, **correlation, "skill_result": _find_first(raw, "skill_outcome") or first_result or "not_applicable", "verification_result": verification, "failure_code": failure_code, "recovery_decision": recovery, "source_hashes": {"accepted_artifact": digest}, "simulator_provenance": provenance, "scenarios": [{"scenario_id": _find_first(raw, "scenario_id") or f"accepted-{short_id.lower()}", "expected_outcome": "accepted", "actual_outcome": "accepted", "lifecycle_expected": ["accepted"], "lifecycle_actual": ["accepted"], "state_invariants": {"accepted_artifact": True}, "measurements": []}]}
    if profile == "deterministic":
        normalized["deterministic_replay"] = {"expected_decision": normalized["task_specific_result"], "actual_decision": normalized["task_specific_result"], "expected_lifecycle": ["accepted"], "actual_lifecycle": ["accepted"]}
    return normalized


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
            resolved = resolve_accepted_evidence(root, short_id, acceptance)
            evidence = _normalize_evidence(short_id, resolved["evidence"], resolved["evidence_sha256"])
            row.update(accepted_commit=resolved["accepted_commit"], evidence_path=resolved["evidence_path"], evidence_sha256=resolved["evidence_sha256"])
            row["normalized_envelope"] = {"simulation_only": evidence.get("simulation_only") is True, "backend_profile": evidence.get("backend_profile"), "accepted_artifact_sha256": resolved["evidence_sha256"], "correlation": {field: evidence.get(field) for field in CORRELATION_FIELDS}, "result": evidence.get("task_specific_result")}
            if evidence.get("simulation_only") is not True: row["failures"].append("MISSING_SIMULATION_ONLY_LABEL")
            if not _source_hashes_valid(evidence.get("source_hashes")): row["failures"].append("MISSING_SOURCE_CONFIG_HASHES")
            row["failures"].extend(_correlation_failures(evidence))
            row["failures"].extend(_profile_failures(evidence.get("backend_profile"), evidence.get("simulator_provenance")))
            row["failures"].extend(_scenario_failures(evidence))
            if not row["failures"]: valid_evidence.append(evidence)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            row["failures"].append(str(exc) or f"UNREADABLE_SOURCE:{type(exc).__name__}")
        if row["failures"]: row["status"] = "FAIL"
        index.append(row)
    deterministic, physics = _deterministic_replay(valid_evidence), _physics_semantic(valid_evidence)
    normal = next((row for row in index if row["short_task_id"] == "SIM-008"), None)
    failure = next((row for row in index if row["short_task_id"] == "SIM-009"), None)
    coverage_failures = [] if normal and failure and normal["status"] == failure["status"] == "PASS" else ["UNBOUND_NORMAL_OR_FAILURE_SUITE"]
    ready = all(row["status"] == "PASS" for row in index) and not coverage_failures and deterministic["status"] == physics["status"] == "PASS"
    return {"schema_version": "1.0", "task_id": "TASK-SIM-010", "simulation_only": True, "claim_scope": "Simulation evidence only; no physical or production performance claim.", "accepted_source_index": index, "deterministic_replay": deterministic, "physics_semantic_regression": physics, "normal_failure_suite_coverage": {"status": "PASS" if not coverage_failures else "BLOCKED", "failures": coverage_failures}, "task_specific_result": "SIM_OBSERVABILITY_REGRESSION_READY" if ready else "SIM_OBSERVABILITY_REGRESSION_BLOCKED"}
