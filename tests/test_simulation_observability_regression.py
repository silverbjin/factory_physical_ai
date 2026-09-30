from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from simulation_runtime.observability_regression import build_regression_evidence


def _write_json(root: Path, relative_path: str, value: dict[str, object]) -> str:
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True) + "\n")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _accepted_fixture(root: Path) -> None:
    expected = {
        "SIM-003": "SIM_BASELINE_READY", "SIM-004": "SIM_NAVIGATION_BACKEND_READY",
        "SIM-005": "SIM_MANIPULATION_BACKEND_READY", "SIM-006": "SIM_VERIFICATION_BACKEND_READY",
        "SIM-007": "SIM_MISSION_INTEGRATION_BLOCKED", "SIM-008": "SIM_NORMAL_E2E_READY",
        "SIM-009": "SIM_FAILURE_SUITE_READY",
    }
    profiles = {"SIM-003": "deterministic", "SIM-004": "gazebo", "SIM-005": "mujoco", "SIM-006": "verification", "SIM-007": "deterministic", "SIM-008": "gazebo", "SIM-009": "mujoco"}
    for short_id, result in expected.items():
        profile = profiles[short_id]
        provenance: dict[str, object] = {}
        if profile == "gazebo":
            provenance = {"ros2_identity": "jazzy", "gazebo_version": "harmonic", "world_model_sha256": "c" * 64, "bridge_sha256": "d" * 64, "launch_sha256": "e" * 64, "simulation_time": 1.0, "wall_time_ms": 10, "bounded_execution": True}
        elif profile == "mujoco":
            provenance = {"mujoco_version": "3", "model_scene_config_sha256": "c" * 64, "seed_identity": "seed-1", "timestep": 0.002, "step_settings": {"steps": 10}, "initial_state_identity": "initial-1"}
        payload: dict[str, object] = {
            "task_id": f"TASK-{short_id}", "task_specific_result": result, "simulation_only": True,
            "backend_profile": profile, "mission_id": "mission-1", "request_id": f"request-{short_id}",
            "action_id": f"action-{short_id}", "trace_id": "trace-1", "skill_result": "success",
            "verification_result": "pass", "failure_code": "NONE", "recovery_decision": "not_required",
            "source_hashes": {"config": "a" * 64}, "simulator_provenance": provenance,
            "scenarios": [{"scenario_id": f"{short_id.lower()}-scenario", "expected_outcome": "success", "actual_outcome": "success", "lifecycle_expected": ["created", "completed"], "lifecycle_actual": ["created", "completed"], "state_invariants": {"contract_valid": True}, "measurements": [{"expected": 1.0, "actual": 1.01, "tolerance": 0.05}]}],
        }
        if profile == "deterministic":
            payload["deterministic_replay"] = {"expected_decision": "complete", "actual_decision": "complete", "expected_lifecycle": ["created", "completed"], "actual_lifecycle": ["created", "completed"]}
        evidence_path = f"results/simulation/{short_id}.json"
        evidence_hash = _write_json(root, evidence_path, payload)
        _write_json(root, f"results/reviews/{short_id}_acceptance.json", {"task_id": f"TASK-{short_id}", "status": "ACCEPT", "accepted_commit": "b" * 40, "evidence": {"path": evidence_path, "sha256": evidence_hash}})


def _row(result: dict[str, object], short_id: str) -> dict[str, object]:
    return next(item for item in result["accepted_source_index"] if item["short_task_id"] == short_id)  # type: ignore[index, return-value]


def test_complete_bound_sources_produce_ready_evidence(tmp_path: Path) -> None:
    _accepted_fixture(tmp_path)
    result = build_regression_evidence(tmp_path)
    assert result["task_specific_result"] == "SIM_OBSERVABILITY_REGRESSION_READY"
    assert result["deterministic_replay"]["status"] == "PASS"  # type: ignore[index]
    assert result["physics_semantic_regression"]["status"] == "PASS"  # type: ignore[index]
    assert result["normal_failure_suite_coverage"]["status"] == "PASS"  # type: ignore[index]


def test_mutated_hash_and_missing_correlation_fail_closed(tmp_path: Path) -> None:
    _accepted_fixture(tmp_path)
    path = tmp_path / "results/simulation/SIM-008.json"
    payload = json.loads(path.read_text())
    del payload["trace_id"]
    path.write_text(json.dumps(payload))
    result = build_regression_evidence(tmp_path)
    assert result["task_specific_result"] == "SIM_OBSERVABILITY_REGRESSION_BLOCKED"
    assert "EVIDENCE_HASH_MISMATCH" in _row(result, "SIM-008")["failures"]  # type: ignore[index]


def test_provenance_replay_and_semantic_failures_are_reported(tmp_path: Path) -> None:
    _accepted_fixture(tmp_path)
    path = tmp_path / "results/simulation/SIM-005.json"
    payload = json.loads(path.read_text())
    payload["simulator_provenance"].pop("seed_identity")
    payload["scenarios"][0]["state_invariants"] = {"contract_valid": False}
    digest = _write_json(tmp_path, "results/simulation/SIM-005.json", payload)
    acceptance = tmp_path / "results/reviews/SIM-005_acceptance.json"
    binding = json.loads(acceptance.read_text()); binding["evidence"]["sha256"] = digest
    acceptance.write_text(json.dumps(binding))
    result = build_regression_evidence(tmp_path)
    failures = _row(result, "SIM-005")["failures"]  # type: ignore[index]
    assert "MISSING_SEED_IDENTITY" in failures
    assert "SCENARIO_INVARIANT_FAILURE:sim-005-scenario" in failures
    assert result["task_specific_result"] == "SIM_OBSERVABILITY_REGRESSION_BLOCKED"


def test_unexpected_predecessor_result_fails_closed(tmp_path: Path) -> None:
    _accepted_fixture(tmp_path)
    path = tmp_path / "results/simulation/SIM-005.json"
    payload = json.loads(path.read_text())
    payload["task_specific_result"] = "SIM_UNEXPECTED_RESULT"
    digest = _write_json(tmp_path, "results/simulation/SIM-005.json", payload)
    acceptance = tmp_path / "results/reviews/SIM-005_acceptance.json"
    binding = json.loads(acceptance.read_text()); binding["evidence"]["sha256"] = digest
    acceptance.write_text(json.dumps(binding))

    result = build_regression_evidence(tmp_path)

    assert "UNEXPECTED_TASK_RESULT" in _row(result, "SIM-005")["failures"]  # type: ignore[index]
    assert result["task_specific_result"] == "SIM_OBSERVABILITY_REGRESSION_BLOCKED"


def test_physics_regression_requires_both_gazebo_and_mujoco_profiles(tmp_path: Path) -> None:
    _accepted_fixture(tmp_path)
    for short_id in ("SIM-005", "SIM-009"):
        path = tmp_path / f"results/simulation/{short_id}.json"
        payload = json.loads(path.read_text())
        payload["backend_profile"] = "deterministic"
        payload["deterministic_replay"] = {
            "expected_decision": "complete", "actual_decision": "complete",
            "expected_lifecycle": ["created", "completed"],
            "actual_lifecycle": ["created", "completed"],
        }
        digest = _write_json(tmp_path, f"results/simulation/{short_id}.json", payload)
        acceptance = tmp_path / f"results/reviews/{short_id}_acceptance.json"
        binding = json.loads(acceptance.read_text()); binding["evidence"]["sha256"] = digest
        acceptance.write_text(json.dumps(binding))

    result = build_regression_evidence(tmp_path)

    assert result["physics_semantic_regression"]["status"] == "BLOCKED"  # type: ignore[index]
    assert "MISSING_REQUIRED_PHYSICS_PROFILE:mujoco" in result["physics_semantic_regression"]["failures"]  # type: ignore[index]
