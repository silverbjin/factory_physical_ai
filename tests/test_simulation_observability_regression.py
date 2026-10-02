from __future__ import annotations

import hashlib
import importlib.util
import json
from copy import deepcopy
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from simulation_runtime.observability_regression import (
    build_regression_evidence,
    classify_regression_failures,
    extract_bound_runs,
    failure_signatures,
    resolve_accepted_evidence,
    resolve_q01_qualification,
    validate_q01_chain,
)

RUNNER_SPEC = importlib.util.spec_from_file_location(
    "run_simulation_observability_regression",
    ROOT / "scripts/run_simulation_observability_regression.py",
)
assert RUNNER_SPEC and RUNNER_SPEC.loader
RUNNER = importlib.util.module_from_spec(RUNNER_SPEC)
RUNNER_SPEC.loader.exec_module(RUNNER)


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
    evidence_paths = {
        "SIM-003": "results/simulation/SIM-003_baseline.json", "SIM-004": "results/simulation/SIM-004_navigation_backend.json",
        "SIM-005": "results/simulation/SIM-005_mujoco_vla_backend.json", "SIM-006": "results/simulation/SIM-006_verification_backend.json",
        "SIM-007": "results/simulation/SIM-007_mission_integration.json", "SIM-008": "results/simulation/SIM-008_normal_system_e2e.json",
        "SIM-009": "results/simulation/SIM-009_failure_recovery.json",
    }
    profiles = {"SIM-003": "deterministic", "SIM-004": "gazebo", "SIM-005": "mujoco", "SIM-006": "verification", "SIM-007": "deterministic", "SIM-008": "gazebo", "SIM-009": "mujoco"}
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=root, check=True)
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
        evidence_path = evidence_paths[short_id]
        evidence_hash = _write_json(root, evidence_path, payload)
        subprocess.run(["git", "add", evidence_path], cwd=root, check=True)
        subprocess.run(["git", "commit", "-qm", f"accepted {short_id}"], cwd=root, check=True)
        commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, text=True, capture_output=True, check=True).stdout.strip()
        _write_json(root, f"results/reviews/{short_id}_acceptance.json", {"task_id": f"TASK-{short_id}", "status": "ACCEPT", "accepted_commit": commit, "evidence": {"path": evidence_path, "sha256": evidence_hash}})


def _row(result: dict[str, object], short_id: str) -> dict[str, object]:
    return next(item for item in result["accepted_source_index"] if item["short_task_id"] == short_id)  # type: ignore[index, return-value]


def _accepted_raw(short_id: str) -> dict[str, object]:
    acceptance = json.loads((ROOT / f"results/reviews/{short_id}_acceptance.json").read_text())
    return resolve_accepted_evidence(ROOT, short_id, acceptance)["evidence"]


def _rebind(root: Path, short_id: str, relative_path: str, digest: str) -> None:
    subprocess.run(["git", "add", relative_path], cwd=root, check=True)
    subprocess.run(["git", "commit", "-qm", f"updated {short_id}"], cwd=root, check=True)
    binding_path = root / f"results/reviews/{short_id}_acceptance.json"
    binding = json.loads(binding_path.read_text())
    binding["accepted_commit"] = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, text=True, capture_output=True, check=True).stdout.strip()
    binding["evidence"]["sha256"] = digest
    binding_path.write_text(json.dumps(binding))


def test_minimal_acceptance_resolves_immutable_evidence_not_worktree(tmp_path: Path) -> None:
    """Catches a resolver that trusts a mutable checkout over accepted provenance."""
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, check=True)
    evidence_path = tmp_path / "results/simulation/SIM-009_failure_recovery.json"
    evidence_path.parent.mkdir(parents=True)
    accepted_payload = {"task_id": "TASK-SIM-009", "task_specific_result": "SIM_FAILURE_SUITE_READY"}
    evidence_path.write_text(json.dumps(accepted_payload))
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-qm", "accepted evidence"], cwd=tmp_path, check=True)
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=tmp_path, text=True, capture_output=True, check=True).stdout.strip()
    evidence_path.write_text(json.dumps({"task_id": "TASK-SIM-009", "task_specific_result": "SIM_WRONG"}))

    resolved = resolve_accepted_evidence(
        tmp_path,
        "SIM-009",
        {"task_id": "TASK-SIM-009", "status": "ACCEPT", "accepted_commit": commit},
    )

    assert resolved["evidence_path"] == "results/simulation/SIM-009_failure_recovery.json"
    assert resolved["evidence"]["task_specific_result"] == "SIM_FAILURE_SUITE_READY"


def test_provenance_only_source_binding_does_not_fail_for_absent_runs(tmp_path: Path) -> None:
    """Catches source rows that confuse binding integrity with run availability."""
    _accepted_fixture(tmp_path)
    path = tmp_path / "results/simulation/SIM-009_failure_recovery.json"
    payload = {"task_id": "TASK-SIM-009", "task_specific_result": "SIM_FAILURE_SUITE_READY"}
    digest = _write_json(tmp_path, "results/simulation/SIM-009_failure_recovery.json", payload)
    _rebind(tmp_path, "SIM-009", "results/simulation/SIM-009_failure_recovery.json", digest)

    result = build_regression_evidence(tmp_path)
    row = _row(result, "SIM-009")

    assert row["status"] == "PASS"
    assert row["failures"] == []
    assert row["run_extraction"]["status"] == "BLOCKED"  # type: ignore[index]
    assert "NO_EXTRACTABLE_RUNS" in row["run_extraction"]["failures"]  # type: ignore[index]
    assert result["task_specific_result"] == "SIM_OBSERVABILITY_REGRESSION_BLOCKED"


def test_preexisting_regression_requires_matching_node_and_stable_signature() -> None:
    baseline = failure_signatures("FAILED tests/test_x.py::test_case - expected 1, got 2\n")
    same = failure_signatures("FAILED tests/test_x.py::test_case - expected 9, got 10\n")
    changed = failure_signatures("FAILED tests/test_x.py::test_case - expected ready, got blocked\n")

    assert classify_regression_failures(same, baseline) == "PROVEN_PREEXISTING"
    assert classify_regression_failures(changed, baseline) == "POSSIBLY_TASK_RELATED"
    assert classify_regression_failures({"test_x": ""}, {"test_x": ""}) == "POSSIBLY_TASK_RELATED"


def test_failure_signatures_extracts_trace_detail_when_summary_reason_is_empty() -> None:
    """Catches parser output that records a node ID with an empty signature."""
    output = """\
_____ ExampleTests.test_case _____
E   AssertionError: expected ready, got blocked
=========================== short test summary info ============================
FAILED tests/test_example.py::ExampleTests::test_case
"""

    signatures = failure_signatures(output)

    assert signatures["tests/test_example.py::ExampleTests::test_case"]


def test_real_predecessor_extractors_preserve_declared_source_paths() -> None:
    """Catches recursive or cross-scenario extraction of accepted E2E evidence."""
    for short_id, required_path in (
        ("SIM-005", "/scenarios/0"),
        ("SIM-008", "/execution"),
        ("SIM-009", "/scenarios/0/result"),
    ):
        acceptance = json.loads((ROOT / f"results/reviews/{short_id}_acceptance.json").read_text())
        resolved = resolve_accepted_evidence(ROOT, short_id, acceptance)
        runs = extract_bound_runs(short_id, resolved["evidence"])

        assert runs
        assert runs[0]["source_json_path"] == required_path
        assert runs[0]["scenario_id"]
        assert runs[0]["identity"]["mission_id"]
        if short_id in {"SIM-008", "SIM-009"}:
            assert runs[0]["identity"]["trace_id"]


def test_run_validation_does_not_reclassify_an_accepted_source_binding(tmp_path: Path) -> None:
    """Run-schema gaps remain visible without corrupting the source index."""
    _accepted_fixture(tmp_path)
    result = build_regression_evidence(tmp_path)
    row = _row(result, "SIM-005")

    assert row["status"] == "PASS"
    assert row["run_extraction"]["status"] == "PASS"  # type: ignore[index]
    assert row["run_validation"]["status"] == "PASS"  # type: ignore[index]


def test_normalized_rows_bind_parent_context_without_nested_scenario_requirement() -> None:
    """A result child inherits only its own parent scenario and artifact context."""
    acceptance = json.loads((ROOT / "results/reviews/SIM-009_acceptance.json").read_text())
    raw = resolve_accepted_evidence(ROOT, "SIM-009", acceptance)["evidence"]
    runs = extract_bound_runs("SIM-009", raw)

    assert runs[0]["source_json_path"] == "/scenarios/0/result"
    assert runs[0]["envelope"]["scenario_source_path"] == "/scenarios/0"
    assert runs[0]["envelope"]["backend_profile"] == "deterministic"
    assert runs[0]["envelope"]["recovery_decision"] == "FAIL_CLOSED"
    assert "scenarios" not in runs[0]["envelope"]


def test_sim007_profile_mapping_is_per_profile_entry() -> None:
    acceptance = json.loads((ROOT / "results/reviews/SIM-007_acceptance.json").read_text())
    raw = resolve_accepted_evidence(ROOT, "SIM-007", acceptance)["evidence"]
    runs = extract_bound_runs("SIM-007", raw)

    assert [(run["scenario_id"], run["envelope"]["backend_profile"]) for run in runs] == [
        ("deterministic", "deterministic"),
        ("navigation_physics", "gazebo"),
        ("manipulation_physics", "mujoco"),
        ("system", "gazebo"),
    ]


def test_complete_historical_sources_without_pinned_q01_stay_blocked(tmp_path: Path) -> None:
    _accepted_fixture(tmp_path)
    result = build_regression_evidence(tmp_path)
    assert result["task_specific_result"] == "SIM_OBSERVABILITY_REGRESSION_BLOCKED"
    assert result["q01_qualification_binding"]["status"] == "BLOCKED"  # type: ignore[index]
    assert result["deterministic_replay"]["status"] == "PASS"  # type: ignore[index]
    assert result["physics_semantic_regression"]["status"] == "BLOCKED"  # type: ignore[index]
    assert result["normal_failure_suite_coverage"]["status"] == "PASS"  # type: ignore[index]


def test_mutated_worktree_evidence_is_ignored_in_favor_of_accepted_blob(tmp_path: Path) -> None:
    _accepted_fixture(tmp_path)
    path = tmp_path / "results/simulation/SIM-008_normal_system_e2e.json"
    payload = json.loads(path.read_text())
    del payload["trace_id"]
    path.write_text(json.dumps(payload))
    result = build_regression_evidence(tmp_path)
    assert result["task_specific_result"] == "SIM_OBSERVABILITY_REGRESSION_BLOCKED"
    assert result["q01_qualification_binding"]["status"] == "BLOCKED"  # type: ignore[index]


def test_provenance_replay_and_semantic_failures_are_reported(tmp_path: Path) -> None:
    _accepted_fixture(tmp_path)
    path = tmp_path / "results/simulation/SIM-005_mujoco_vla_backend.json"
    payload = json.loads(path.read_text())
    payload["simulator_provenance"].pop("seed_identity")
    payload["scenarios"][0]["state_invariants"] = {"contract_valid": False}
    digest = _write_json(tmp_path, "results/simulation/SIM-005_mujoco_vla_backend.json", payload)
    _rebind(tmp_path, "SIM-005", "results/simulation/SIM-005_mujoco_vla_backend.json", digest)
    result = build_regression_evidence(tmp_path)
    failures = _row(result, "SIM-005")["run_validation"]["failures"]  # type: ignore[index]
    assert "RUN[0]:MISSING_SEED_IDENTITY" in failures
    assert "RUN[0]:SCENARIO_ASSERTION_FAILED:sim-005-scenario" in failures
    assert result["task_specific_result"] == "SIM_OBSERVABILITY_REGRESSION_BLOCKED"


def test_unexpected_predecessor_result_fails_closed(tmp_path: Path) -> None:
    _accepted_fixture(tmp_path)
    path = tmp_path / "results/simulation/SIM-005_mujoco_vla_backend.json"
    payload = json.loads(path.read_text())
    payload["task_specific_result"] = "SIM_UNEXPECTED_RESULT"
    digest = _write_json(tmp_path, "results/simulation/SIM-005_mujoco_vla_backend.json", payload)
    _rebind(tmp_path, "SIM-005", "results/simulation/SIM-005_mujoco_vla_backend.json", digest)

    result = build_regression_evidence(tmp_path)

    assert "UNEXPECTED_TASK_RESULT" in _row(result, "SIM-005")["failures"]  # type: ignore[index]
    assert result["task_specific_result"] == "SIM_OBSERVABILITY_REGRESSION_BLOCKED"


def test_physics_regression_requires_both_gazebo_and_mujoco_profiles(tmp_path: Path) -> None:
    _accepted_fixture(tmp_path)
    paths = {"SIM-005": "results/simulation/SIM-005_mujoco_vla_backend.json", "SIM-009": "results/simulation/SIM-009_failure_recovery.json"}
    for short_id, relative_path in paths.items():
        path = tmp_path / relative_path
        payload = json.loads(path.read_text())
        payload["backend_profile"] = "deterministic"
        payload["deterministic_replay"] = {
            "expected_decision": "complete", "actual_decision": "complete",
            "expected_lifecycle": ["created", "completed"],
            "actual_lifecycle": ["created", "completed"],
        }
        digest = _write_json(tmp_path, relative_path, payload)
        _rebind(tmp_path, short_id, relative_path, digest)

    result = build_regression_evidence(tmp_path)

    assert result["physics_semantic_regression"]["status"] == "BLOCKED"  # type: ignore[index]
    assert "MISSING_REQUIRED_PHYSICS_PROFILE:mujoco" in result["physics_semantic_regression"]["failures"]  # type: ignore[index]


def test_sim004_binds_exact_assets_and_action_keyed_lifecycle() -> None:
    raw = _accepted_raw("SIM-004")
    runs = extract_bound_runs("SIM-004", raw)
    success = next(run["envelope"] for run in runs if run["scenario_id"] == "success")
    provenance = success["simulator_provenance"]

    assert provenance["bridge_sha256"] == "9ec6f3ae8b995e07275fdbd7e9c8a0cc50a7b441b9e7add028a76e75690d9c0e"
    assert provenance["launch_sha256"] == "389b372392de00810ea62baa724510b795918a25dbb11c41b4ab3ac16644c112"
    assert provenance["wall_time_ms"] == 5736.032
    assert provenance["bounded_execution"] == {
        "execution_bound_ms": 30000,
        "cleanup_complete": True,
        "cleanup_bound_ms": 5000,
    }
    assert provenance["simulation_time"] is None
    assert success["provenance_authority"]["bridge_sha256"] == "/provenance/assets/0/sha256"
    assert success["provenance_authority"]["launch_sha256"] == "/provenance/assets/2/sha256"
    assert success["provenance_authority"]["wall_time_ms"] == "/bounded_lifecycle/executions/0/duration_ms"


def test_sim004_lifecycle_never_joins_by_position() -> None:
    raw = deepcopy(_accepted_raw("SIM-004"))
    raw["bounded_lifecycle"]["executions"][0]["action_id"] = "different-action"  # type: ignore[index]
    success = next(
        run["envelope"]
        for run in extract_bound_runs("SIM-004", raw)
        if run["scenario_id"] == "success"
    )

    assert success["simulator_provenance"]["wall_time_ms"] is None
    assert success["simulator_provenance"]["bounded_execution"] is None


def test_sim005_preserves_ids_and_exact_mujoco_provenance_without_trace() -> None:
    run = extract_bound_runs("SIM-005", _accepted_raw("SIM-005"))[0]["envelope"]

    assert run["mission_id"] == "db42b4f4-2a97-4ad8-9cf5-753d121998ef"
    assert run["request_id"] == "e2d6113b-a955-4e4f-b269-e12ceb363469"
    assert run["action_id"] == "b3c82456-4c35-4ddc-8088-6b79b8b4fae3"
    assert run["trace_id"] is None
    assert run["source_hashes"] == {
        "backend_source_sha256": "61cc33fbddae862c937d350c0baf8015ff6485605ac6267e7aadcff9cf19db2f",
        "runner_source_sha256": "561f2f0dc9e9ca7ae31dcb0343fcf7e515b0bc3b2aaf8b25f8fe44d39b471902",
        "model_config_sha256": "34c0900610d69e5f7500bcf0121490c984a62b20943e89dd3bc7d5c0c87b84a9",
        "model_scene_sha256": "21fcb775690b058285480d77c96c788779bd8e7aaced663ba6eeda4691dfd160",
    }
    assert run["simulator_provenance"]["model_scene_config_sha256"] == {
        "config": "34c0900610d69e5f7500bcf0121490c984a62b20943e89dd3bc7d5c0c87b84a9",
        "scene": "21fcb775690b058285480d77c96c788779bd8e7aaced663ba6eeda4691dfd160",
    }


def test_sim007_profile_smoke_is_aggregate_and_accepted_failures_are_not_regressions() -> None:
    runs = extract_bound_runs("SIM-007", _accepted_raw("SIM-007"))
    navigation = next(run["envelope"] for run in runs if run["scenario_id"] == "navigation_physics")

    assert navigation["record_kind"] == "profile_aggregate"
    assert navigation["action_ids"] == [None, None, None]
    assert navigation["requires_operation_identity"] is False
    assert navigation["accepted_outcome"] == "failure"
    assert navigation["observed_outcome"] == "failure"
    assert navigation["failure_code"] == "PROFILE_UNAVAILABLE"
    assert navigation["scenario_pass"] is True


def test_sim009_verification_semantics_stay_with_their_scenario() -> None:
    runs = extract_bound_runs("SIM-009", _accepted_raw("SIM-009"))
    mismatch = next(run["envelope"] for run in runs if run["scenario_id"] == "SIM009-VERIFY-MISMATCH")
    stale = next(run["envelope"] for run in runs if run["scenario_id"] == "SIM009-VERIFY-STALE")
    uncertain = next(run["envelope"] for run in runs if run["scenario_id"] == "SIM009-VERIFY-UNCERTAIN")

    assert mismatch["verification_result"] == "fail"
    assert mismatch["failure_code"] == "EXPECTED_STATE_MISMATCH"
    assert mismatch["recovery_decision"] == "RECOVERY"
    assert stale["verification_result"] is None
    assert stale["verification_operational_failure"] is True
    assert stale["failure_code"] == "INVALID_VERIFICATION_EVIDENCE"
    assert uncertain["verification_result"] == "uncertain"
    assert uncertain["failure_code"] == "INSUFFICIENT_OR_AMBIGUOUS_EVIDENCE"


def test_sim009_unavailable_operation_does_not_invent_physics_applicability() -> None:
    unavailable = next(
        run["envelope"]
        for run in extract_bound_runs("SIM-009", _accepted_raw("SIM-009"))
        if run["scenario_id"] == "SIM009-L0-UNAVAILABLE"
    )

    assert unavailable["physics_semantic_applicable"] is False
    assert unavailable["required_provenance_fields"] == ()
    assert unavailable["required_source_hash_fields"] == ("manifest_sha256",)


def test_sim009_cross_scenario_values_are_never_used() -> None:
    raw = deepcopy(_accepted_raw("SIM-009"))
    raw["scenarios"][13]["verification"].pop("verdict")  # type: ignore[index]
    raw["scenarios"][13]["verification"].pop("mismatch_code")  # type: ignore[index]
    mismatch = next(
        run["envelope"]
        for run in extract_bound_runs("SIM-009", raw)
        if run["scenario_id"] == "SIM009-VERIFY-MISMATCH"
    )

    assert mismatch["verification_result"] is None
    assert mismatch["failure_code"] is None


def test_sim008_does_not_alias_scenario_config_as_bridge_and_launch() -> None:
    run = extract_bound_runs("SIM-008", _accepted_raw("SIM-008"))[0]["envelope"]
    provenance = run["simulator_provenance"]

    assert provenance["bridge_sha256"] is None
    assert provenance["launch_sha256"] is None
    assert run["source_hashes"]["scenario_config"] not in {
        provenance["bridge_sha256"], provenance["launch_sha256"]
    }


def test_sim009_backend_qualification_requires_exact_binding_and_component_version() -> None:
    support = {
        short_id: resolve_accepted_evidence(
            ROOT,
            short_id,
            json.loads((ROOT / f"results/reviews/{short_id}_acceptance.json").read_text()),
        )
        for short_id in ("SIM-004", "SIM-005")
    }
    raw = _accepted_raw("SIM-009")
    runs = extract_bound_runs("SIM-009", raw, support)
    gazebo = next(run["envelope"] for run in runs if run["scenario_id"] == "SIM009-NAV-BLOCKED")
    mujoco = next(run["envelope"] for run in runs if run["scenario_id"] == "SIM009-VLA-GRASP-MISS")

    assert gazebo["backend_qualification"]["source_task"] == "SIM-004"
    assert gazebo["backend_qualification_authority"] == "/accepted_bindings/SIM-004"
    assert mujoco["backend_qualification"]["source_task"] == "SIM-005"
    assert gazebo["simulator_provenance"].get("simulation_time") is None
    assert mujoco["source_hashes"].get("run_config_sha256") is None

    wrong_support = deepcopy(support)
    wrong_support["SIM-004"]["accepted_commit"] = "0" * 40
    rebound = extract_bound_runs("SIM-009", raw, wrong_support)
    rebound_gazebo = next(run["envelope"] for run in rebound if run["scenario_id"] == "SIM009-NAV-BLOCKED")
    assert rebound_gazebo["backend_qualification"] is None

    wrong_profile = deepcopy(raw)
    wrong_profile["scenarios"][3]["backend"] = "mujoco"  # type: ignore[index]
    mismatched = extract_bound_runs("SIM-009", wrong_profile, support)
    mismatched_run = next(run["envelope"] for run in mismatched if run["scenario_id"] == "SIM009-NAV-BLOCKED")
    assert mismatched_run["backend_qualification"] is None


def test_q01_binding_replaces_only_downstream_gate_blockers_not_history() -> None:
    result = build_regression_evidence(ROOT)
    sim004 = _row(result, "SIM-004")["run_validation"]["failures"]  # type: ignore[index]
    sim005 = _row(result, "SIM-005")["run_validation"]["failures"]  # type: ignore[index]
    sim007 = _row(result, "SIM-007")["run_validation"]["failures"]  # type: ignore[index]
    sim008 = _row(result, "SIM-008")["run_validation"]["failures"]  # type: ignore[index]
    sim009 = _row(result, "SIM-009")["run_validation"]["failures"]  # type: ignore[index]

    assert any(failure.endswith("MISSING_SIMULATION_TIME") for failure in sim004)
    assert "RUN[0]:MISSING_BRIDGE_SHA256" not in sim004
    assert "RUN[0]:MISSING_LAUNCH_SHA256" not in sim004
    assert "RUN[0]:MISSING_WALL_TIME_MS" not in sim004
    assert "RUN[0]:MISSING_BOUNDED_EXECUTION" not in sim004
    assert all("MISSING_TRACE_ID" in failure or "INCOMPLETE_CORRELATION_IDENTITY" in failure for failure in sim005)
    assert any(failure.endswith("MISSING_SOURCE_CONFIG_HASHES") for failure in sim007)
    assert not any("MISSING_REQUEST_ID" in failure or "MISSING_ACTION_ID" in failure for failure in sim007)
    assert not any("SCENARIO_ASSERTION_FAILED" in failure for failure in sim007)
    assert "RUN[0]:MISSING_BRIDGE_SHA256" in sim008
    assert "RUN[0]:MISSING_LAUNCH_SHA256" in sim008
    assert not any("MISSING_FAILURE_CODE" in failure or "MISSING_VERIFICATION_RESULT" in failure for failure in sim009)
    assert any("MISSING_SOURCE_HASH:run_config_sha256" in failure for failure in sim009)
    sim009_row = _row(result, "SIM-009")
    assert set(sim009_row["declared_scenario_ids"]) == {  # type: ignore[arg-type]
        source["scenario_id"] for source in sim009_row["run_sources"]  # type: ignore[index]
    }
    assert result["normal_failure_suite_coverage"]["status"] == "PASS"  # type: ignore[index]
    assert result["task_specific_result"] == "SIM_OBSERVABILITY_REGRESSION_READY"


def _q01_chain() -> tuple[dict[str, object], dict[str, object]]:
    acceptance = json.loads(
        subprocess.run(
            ["git", "show", "a1f1539c27f61fb2ce52aed33ceaf1bfe343912c:results/reviews/SIM-Q01-MIN_acceptance.json"],
            cwd=ROOT, text=True, capture_output=True, check=True,
        ).stdout
    )
    evidence = json.loads(
        subprocess.run(
            ["git", "show", "b55bc4fc2435e83c3761457b92d9e14892e39435:results/simulation/SIM-Q01_provenance_qualification.json"],
            cwd=ROOT, text=True, capture_output=True, check=True,
        ).stdout
    )
    return acceptance, evidence


def test_q01_pinned_chain_and_exact_subjects_pass() -> None:
    resolved = resolve_q01_qualification(ROOT)
    subjects = resolved["qualification_subjects"]
    assert resolved["acceptance_task_id"] == "TASK-SIM-Q01-MIN"
    assert resolved["evidence_task_id"] == "TASK-SIM-Q01"
    assert len(subjects) == 11
    assert {item["subject_id"] for item in subjects} == {
        "q01-sim008-normal-system-authority", "q01-sim009-SIM009-NAV-BLOCKED",
        "q01-sim009-SIM009-NAV-ABORTED", "q01-sim009-SIM009-NAV-TIMEOUT-RETRY",
        "q01-sim009-SIM009-NAV-TF-UNAVAILABLE", "q01-sim009-SIM009-VLA-GRASP-MISS",
        "q01-sim009-SIM009-VLA-CONTACT-LOSS", "q01-sim009-SIM009-VLA-WORKSPACE-LIMIT",
        "q01-sim009-SIM009-VLA-TIMEOUT", "q01-sim009-SIM009-VLA-AMBIGUOUS",
        "q01-sim009-SIM009-VLA-UNKNOWN",
    }
    assert all(item["replay_applicable"] is False for item in subjects)


@pytest.mark.parametrize(
    ("target", "value"),
    [
        ("status", "REJECT"), ("workflow_complete", False),
        ("accepted_commit", "0" * 40),
    ],
)
def test_q01_acceptance_contract_fails_closed(target: str, value: object) -> None:
    acceptance, evidence = _q01_chain()
    acceptance[target] = value
    with pytest.raises(ValueError):
        validate_q01_chain(ROOT, acceptance, evidence)


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("task_id",), "TASK-SIM-Q01-MIN"),
        (("task_specific_result",), "SIM_WRONG"),
        (("qualification_subjects", 0, "claim_scope"), "historical_oracle"),
        (("qualification_subjects", 0, "predecessor_binding", "evidence_sha256"), "0" * 64),
        (("qualification_subjects", 0, "applicability", "physics_measurement", "state"), "UNKNOWN"),
    ],
)
def test_q01_evidence_contract_fails_closed(path: tuple[object, ...], value: object) -> None:
    acceptance, evidence = _q01_chain()
    target: object = evidence
    for key in path[:-1]:
        target = target[key]  # type: ignore[index]
    target[path[-1]] = value  # type: ignore[index]
    with pytest.raises(ValueError):
        validate_q01_chain(ROOT, acceptance, evidence)


def test_q01_rejects_duplicate_and_extra_subjects() -> None:
    acceptance, evidence = _q01_chain()
    duplicate = deepcopy(evidence["qualification_subjects"][0])  # type: ignore[index]
    evidence["qualification_subjects"].append(duplicate)  # type: ignore[index]
    with pytest.raises(ValueError):
        validate_q01_chain(ROOT, acceptance, evidence)


def test_runner_binds_one_explicit_interpreter_to_identical_commands() -> None:
    python = Path(sys.executable)
    candidate = RUNNER.regression_command(python)
    baseline = RUNNER.regression_command(python)

    assert candidate == baseline
    assert candidate == [str(python), "-m", "pytest", "-q", "-p", "no:cacheprovider"]


def test_runner_rejects_missing_and_non_executable_interpreters(tmp_path: Path) -> None:
    missing = tmp_path / "missing-python"
    non_executable = tmp_path / "python"
    non_executable.write_text("#!/bin/sh\n")

    with pytest.raises(RuntimeError, match="QUALIFIED_PYTHON"):
        RUNNER.resolve_qualified_python(missing)
    with pytest.raises(RuntimeError, match="QUALIFIED_PYTHON"):
        RUNNER.resolve_qualified_python(non_executable)


def test_runner_dependency_preflight_and_source_probe_use_resolved_python() -> None:
    python = RUNNER.resolve_qualified_python(Path(sys.executable))
    preflight = RUNNER.preflight_environment(python)
    probe = RUNNER.probe_worktree_environment(ROOT, python)

    assert preflight["python_executable"] == str(python)
    assert preflight["mujoco_version"] == "3.13.0"
    assert probe["python_executable"] == str(python)
    assert Path(probe["project_module_origin"]).is_relative_to(ROOT)


def test_runner_dependency_preflight_failure_is_fail_closed(tmp_path: Path) -> None:
    fake_python = tmp_path / "python"
    fake_python.write_text("#!/bin/sh\nexit 7\n")
    fake_python.chmod(0o755)

    with pytest.raises(RuntimeError, match="DEPENDENCY_PREFLIGHT_FAILED"):
        RUNNER.preflight_environment(fake_python)


def test_environment_and_collection_failures_cannot_be_preexisting() -> None:
    matching = {"tests/test_x.py::test_case": "signature"}

    assert RUNNER.classify_execution(2, 2, matching, matching) == "POSSIBLY_TASK_RELATED"
    assert RUNNER.classify_execution(1, 2, matching, matching) == "POSSIBLY_TASK_RELATED"
    assert RUNNER.classify_execution(1, 1, matching, matching, "cleanup failed") == "POSSIBLY_TASK_RELATED"
    assert RUNNER.classify_execution(1, 1, matching, matching) == "PROVEN_PREEXISTING"
