from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from simulation_runtime.provenance_qualification import QualificationSubject, resolve_predecessor_binding, validate_subject


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
