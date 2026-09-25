from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from simulation_runtime.provenance_qualification import QualificationSubject, aggregate_qualification_evidence, collect_sim009_scenario_qualifications, collect_sim008_configuration_qualification, collect_sim007_profile_qualifications, build_mujoco_subject, build_gazebo_subject, resolve_predecessor_binding, validate_subject


def _operation(**changes: object) -> QualificationSubject:
    value = {
        "subject_id": "q01-sim004-success-time",
        "record_kind": "operation_run",
        "claim_scope": "run_local",
        "predecessor_binding": {"task_id": "TASK-SIM-004", "accepted_commit": "a" * 40, "evidence_path": "results/simulation/SIM-004_navigation_backend.json", "evidence_sha256": "b" * 64},
        "qualification_run_id": "new-run-1",
        "scenario_id": "success",
        "backend_id": "gazebo",
        "component_version": "v1",
        "configuration_provenance": {"bridge": "c" * 64, "launch": "d" * 64},
        "world_model_provenance": {"world": "e" * 64},
        "timing": {"simulation_time": 1.0, "wall_time_ms": 2.0, "bounded_execution": True},
        "semantic_outcome": {"result": "success"},
    }
    value.update(changes)
    return QualificationSubject(**value)


def test_operation_subject_requires_distinct_semantic_asset_hashes() -> None:
    with pytest.raises(ValueError, match="SEMANTIC_HASH_ALIAS"):
        validate_subject(_operation(configuration_provenance={"bridge": "c" * 64, "launch": "c" * 64}))


def test_operation_subject_rejects_fake_not_applicable() -> None:
    with pytest.raises(ValueError, match="FAKE_NOT_APPLICABLE"):
        validate_subject(_operation(scenario_id="not_applicable"))


def test_minimal_valid_subjects_cover_all_record_kinds() -> None:
    assert validate_subject(_operation()) is None
    aggregate = _operation(subject_id="q01-sim007-system", record_kind="profile_aggregate", claim_scope="profile", qualification_run_id=None, scenario_id=None, backend_id="system", profile_id="system", correlation_identity=None, timing=None)
    assert validate_subject(aggregate) is None
    version = _operation(subject_id="q01-version", record_kind="version_qualification", claim_scope="version", qualification_run_id=None, scenario_id=None, timing=None)
    assert validate_subject(version) is None


def test_resolver_reads_accepted_git_blob_not_mutated_worktree(tmp_path: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "q01@example.invalid"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Q01"], cwd=tmp_path, check=True)
    path = tmp_path / "results/simulation/SIM-004_navigation_backend.json"
    path.parent.mkdir(parents=True)
    accepted = {"task_id": "TASK-SIM-004", "task_specific_result": "SIM_NAVIGATION_BACKEND_READY"}
    path.write_text(json.dumps(accepted))
    subprocess.run(["git", "add", "results"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-qm", "accepted"], cwd=tmp_path, check=True)
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=tmp_path, text=True).strip()
    path.write_text(json.dumps({"task_id": "TASK-SIM-004", "task_specific_result": "WRONG"}))
    binding = resolve_predecessor_binding(tmp_path, "TASK-SIM-004", {"task_id": "TASK-SIM-004", "status": "ACCEPT", "accepted_commit": commit}, "results/simulation/SIM-004_navigation_backend.json")
    assert binding.evidence["task_specific_result"] == "SIM_NAVIGATION_BACKEND_READY"


def test_gazebo_collector_requires_structured_simulator_time() -> None:
    with pytest.raises(ValueError, match="MISSING_STRUCTURED_SIMULATION_TIME"):
        build_gazebo_subject(_operation(), {"wall_time_ms": 2.0, "stdout": "time=1"})


def test_mujoco_new_run_requires_trace_and_rejects_historical_injection() -> None:
    with pytest.raises(ValueError, match="MISSING_TRACE_ID"):
        build_mujoco_subject(_operation(backend_id="mujoco"), {"new_run": True})
    with pytest.raises(ValueError, match="HISTORICAL_TRACE_INJECTION"):
        build_mujoco_subject(_operation(backend_id="mujoco"), {"new_run": False, "trace_id": "trace"})


def test_sim007_collector_uses_accepted_blob_for_profile_local_aggregate_qualification() -> None:
    """Removing the collector or its frozen-blob binding must fail this test."""
    acceptance = json.loads((ROOT / "results/reviews/SIM-007_acceptance.json").read_text())
    binding = resolve_predecessor_binding(
        ROOT,
        "TASK-SIM-007",
        acceptance,
        "results/simulation/SIM-007_mission_integration.json",
    )

    subjects = collect_sim007_profile_qualifications(ROOT, binding)

    assert [subject.profile_id for subject in subjects] == [
        "deterministic",
        "navigation_physics",
        "manipulation_physics",
        "system",
    ]
    assert all(subject.record_kind == "profile_aggregate" for subject in subjects)
    assert all(subject.qualification_run_id is None for subject in subjects)
    assert all(subject.scenario_id is None for subject in subjects)
    assert all(subject.predecessor_binding == {
        "task_id": binding.task_id,
        "accepted_commit": binding.accepted_commit,
        "evidence_path": binding.evidence_path,
        "evidence_sha256": binding.evidence_sha256,
    } for subject in subjects)
    assert all(set(subject.configuration_provenance) == {"profile_source"} for subject in subjects)
    assert len({next(iter(subject.configuration_provenance.values())) for subject in subjects}) == 4
    assert all(subject.authority_paths == {
        "profile_source": f"{binding.accepted_commit}:{binding.evidence_path}#/profiles/{subject.profile_id}",
        "profile_runtime_context": f"{binding.accepted_commit}:{binding.evidence_path}#/profile_smoke/{index}",
        "component_version": f"{binding.accepted_commit}:src/simulation_runtime/mission_integration.py",
    } for index, subject in enumerate(subjects))
    assert all(subject.semantic_outcome is not None for subject in subjects)
    assert next(subject for subject in subjects if subject.profile_id == "system").semantic_outcome == {
        "mission_result": "failure",
        "failure_code": "PROFILE_UNAVAILABLE",
    }


def test_sim008_qualifier_rejects_generic_or_misbound_configuration_authority() -> None:
    acceptance = json.loads((ROOT / "results/reviews/SIM-008_acceptance.json").read_text())
    binding = resolve_predecessor_binding(ROOT, "TASK-SIM-008", acceptance, "results/simulation/SIM-008_normal_system_e2e.json")
    with pytest.raises(ValueError, match="MISSING_STRUCTURED_SIMULATION_TIME"):
        collect_sim008_configuration_qualification(ROOT, binding, {})
    subject = collect_sim008_configuration_qualification(ROOT, binding, {"simulation_time": 1.0, "bounded_execution": True})
    assert subject.configuration_provenance.keys() == {"bridge_configuration", "launch_run_configuration"}
    assert subject.configuration_provenance["bridge_configuration"] != subject.configuration_provenance["launch_run_configuration"]
    with pytest.raises(ValueError, match="SEMANTIC_HASH_ALIAS"):
        validate_subject(QualificationSubject(**{**subject.__dict__, "configuration_provenance": {"bridge_configuration": "a" * 64, "launch_run_configuration": "a" * 64}}))


def test_sim009_collector_requires_per_scenario_run_local_measurement() -> None:
    acceptance = json.loads((ROOT / "results/reviews/SIM-009_acceptance.json").read_text())
    binding = resolve_predecessor_binding(ROOT, "TASK-SIM-009", acceptance, "results/simulation/SIM-009_failure_recovery.json")
    with pytest.raises(ValueError, match="MISSING_SCENARIO_MEASUREMENT"):
        collect_sim009_scenario_qualifications(binding, {})


def test_aggregator_rejects_duplicate_subject_identity() -> None:
    with pytest.raises(ValueError, match="DUPLICATE_QUALIFICATION_SUBJECT"):
        aggregate_qualification_evidence([_operation(), _operation()], "a" * 40)
