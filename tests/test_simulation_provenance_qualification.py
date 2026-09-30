from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from simulation_runtime.provenance_qualification import QualificationSubject, collect_sim009_execution_result, collect_sim008_execution_result, collect_sim005_execution_result, collect_sim004_execution_result, aggregate_qualification_evidence, read_gazebo_simulation_time, render_qualification_report, write_qualification_artifacts, collect_sim009_scenario_qualifications, collect_sim008_configuration_qualification, collect_sim007_profile_qualifications, build_mujoco_subject, build_gazebo_subject, resolve_predecessor_binding, validate_subject
from scripts import q01_execution_adapters
from scripts import run_simulation_provenance_qualification
from scripts.q01_execution_adapters import _sim009_sidecar_observation, gazebo_clock, run_sim005_qualification, run_sim008_qualification, run_sim009_qualification
from scripts.run_simulation_provenance_qualification import collect_qualification_subjects, required_subject_manifest


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


def test_min_q01_applicability_requires_explicit_structural_not_applicable_state() -> None:
    subject = _operation(
        subject_id="q01-sim009-SIM009-VLA-UNKNOWN",
        predecessor_binding={"task_id": "TASK-SIM-009", "accepted_commit": "a" * 40, "evidence_path": "results/simulation/SIM-009_failure_recovery.json", "evidence_sha256": "b" * 64},
        scenario_id="SIM009-VLA-UNKNOWN",
        timing={"simulation_time_source": "mujoco_no_physics_start", "execution_state": {"simulator_started": False, "physics_started": False}},
        applicability={
            "structured_simulator_time": {"state": "NOT_APPLICABLE", "justification": "TERMINATED_BEFORE_SIMULATOR_PHYSICS", "execution_state": {"simulator_started": False, "physics_started": False}},
            "physics_measurement": {"state": "NOT_APPLICABLE", "justification": "TERMINATED_BEFORE_SIMULATOR_PHYSICS", "execution_state": {"simulator_started": False, "physics_started": False}},
        },
    )
    assert validate_subject(subject) is None
    with pytest.raises(ValueError, match="INVALID_NOT_APPLICABLE_EXECUTION_STATE"):
        validate_subject(QualificationSubject(**{**subject.__dict__, "applicability": {**subject.applicability, "structured_simulator_time": {"state": "NOT_APPLICABLE"}}}))


def test_physics_executed_min_q01_subject_requires_actual_physics_measurement() -> None:
    subject = _operation(
        subject_id="q01-sim009-SIM009-NAV-BLOCKED",
        predecessor_binding={"task_id": "TASK-SIM-009", "accepted_commit": "a" * 40, "evidence_path": "results/simulation/SIM-009_failure_recovery.json", "evidence_sha256": "b" * 64},
        scenario_id="SIM009-NAV-BLOCKED",
        applicability={"structured_simulator_time": {"state": "REQUIRED"}, "physics_measurement": {"state": "OPTIONAL"}},
    )
    with pytest.raises(ValueError, match="INVALID_PHYSICS_APPLICABILITY"):
        validate_subject(subject)
    with pytest.raises(ValueError, match="MISSING_PHYSICS_MEASUREMENT"):
        validate_subject(QualificationSubject(**{**subject.__dict__, "applicability": {"structured_simulator_time": {"state": "REQUIRED"}, "physics_measurement": {"state": "REQUIRED"}}}))


def test_frozen_contract_b_binding_rejects_mutable_acceptance_pointer() -> None:
    acceptance = json.loads((ROOT / "results/reviews/SIM-008_acceptance.json").read_text())
    expected = run_simulation_provenance_qualification.FROZEN["TASK-SIM-008"]
    with pytest.raises(ValueError, match="FROZEN_ACCEPTED_COMMIT_MISMATCH"):
        resolve_predecessor_binding(
            ROOT,
            "TASK-SIM-008",
            {**acceptance, "accepted_commit": "0" * 40},
            expected["evidence_path"],
            expected_binding=expected,
        )
    with pytest.raises(ValueError, match="FROZEN_EVIDENCE_PATH_MISMATCH"):
        resolve_predecessor_binding(
            ROOT,
            "TASK-SIM-008",
            {**acceptance, "evidence": {**acceptance["evidence"], "path": "results/simulation/other.json"}},
            expected["evidence_path"],
            expected_binding=expected,
        )
    with pytest.raises(ValueError, match="FROZEN_EVIDENCE_SHA256_MISMATCH"):
        resolve_predecessor_binding(
            ROOT,
            "TASK-SIM-008",
            {**acceptance, "evidence": {**acceptance["evidence"], "sha256": "0" * 64}},
            expected["evidence_path"],
            expected_binding=expected,
        )
    with pytest.raises(ValueError, match="FROZEN_TASK_RESULT_MISMATCH"):
        resolve_predecessor_binding(
            ROOT,
            "TASK-SIM-008",
            acceptance,
            expected["evidence_path"],
            expected_binding={**expected, "task_specific_result": "WRONG"},
        )


def test_aggregator_blocks_extra_or_misbound_min_q01_subjects() -> None:
    subject = _operation(
        subject_id="q01-sim009-SIM009-NAV-BLOCKED",
        predecessor_binding={"task_id": "TASK-SIM-009", "accepted_commit": "a" * 40, "evidence_path": "results/simulation/SIM-009_failure_recovery.json", "evidence_sha256": "b" * 64},
        scenario_id="SIM009-NAV-BLOCKED",
        timing={"simulation_time": 1.0, "physics_measurement": {"source": "test", "seconds": 1.0}, "wall_time_ms": 2.0, "bounded_execution": True},
        applicability={"structured_simulator_time": {"state": "REQUIRED"}, "physics_measurement": {"state": "REQUIRED"}},
    )
    evidence = aggregate_qualification_evidence(
        [subject], "a" * 40, required_subject_ids={subject.subject_id},
        required_subject_bindings={subject.subject_id: {"task_id": "TASK-SIM-009", "scenario_id": "WRONG"}},
    )
    assert evidence["task_specific_result"] == "SIM_PROVENANCE_QUALIFICATION_BLOCKED"
    assert evidence["validation"]["binding_error_subject_ids"] == [subject.subject_id]


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


def test_frozen_contract_b_acceptance_supports_minimal_and_validates_rich_binding(tmp_path: Path) -> None:
    """The frozen Contract-B binding, not Acceptance duplication, authenticates Evidence."""
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "q01@example.invalid"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Q01"], cwd=tmp_path, check=True)
    path = tmp_path / "results/simulation/SIM-004_navigation_backend.json"
    path.parent.mkdir(parents=True)
    evidence = {"task_id": "TASK-SIM-004", "task_specific_result": "SIM_NAVIGATION_BACKEND_READY"}
    path.write_text(json.dumps(evidence))
    subprocess.run(["git", "add", "results"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-qm", "accepted"], cwd=tmp_path, check=True)
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=tmp_path, text=True).strip()
    evidence_path = "results/simulation/SIM-004_navigation_backend.json"
    evidence_sha256 = hashlib.sha256(path.read_bytes()).hexdigest()
    expected = {
        "task_id": "TASK-SIM-004", "accepted_commit": commit,
        "evidence_path": evidence_path, "evidence_sha256": evidence_sha256,
        "task_specific_result": "SIM_NAVIGATION_BACKEND_READY",
    }
    minimal = {"task_id": "TASK-SIM-004", "status": "ACCEPT", "accepted_commit": commit}

    assert resolve_predecessor_binding(tmp_path, "TASK-SIM-004", minimal, evidence_path, expected_binding=expected).evidence == evidence
    rich = {**minimal, "evidence": {"path": evidence_path, "sha256": evidence_sha256}}
    assert resolve_predecessor_binding(tmp_path, "TASK-SIM-004", rich, evidence_path, expected_binding=expected).evidence == evidence
    with pytest.raises(ValueError, match="FROZEN_EVIDENCE_PATH_MISMATCH"):
        resolve_predecessor_binding(tmp_path, "TASK-SIM-004", {**rich, "evidence": {**rich["evidence"], "path": "results/other.json"}}, evidence_path, expected_binding=expected)
    with pytest.raises(ValueError, match="FROZEN_EVIDENCE_SHA256_MISMATCH"):
        resolve_predecessor_binding(tmp_path, "TASK-SIM-004", {**rich, "evidence": {**rich["evidence"], "sha256": "0" * 64}}, evidence_path, expected_binding=expected)
    with pytest.raises(ValueError, match="FROZEN_EVIDENCE_SHA256_MISMATCH"):
        resolve_predecessor_binding(tmp_path, "TASK-SIM-004", minimal, evidence_path, expected_binding={**expected, "evidence_sha256": "0" * 64})
    with pytest.raises(ValueError, match="FROZEN_ACCEPTED_COMMIT_MISMATCH"):
        resolve_predecessor_binding(tmp_path, "TASK-SIM-004", {**minimal, "accepted_commit": "0" * 40}, evidence_path, expected_binding=expected)
    with pytest.raises(ValueError, match="FROZEN_TASK_RESULT_MISMATCH"):
        resolve_predecessor_binding(tmp_path, "TASK-SIM-004", minimal, evidence_path, expected_binding={**expected, "task_specific_result": "WRONG"})


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


def test_artifact_writer_derives_json_and_report_from_blocked_evidence(tmp_path: Path) -> None:
    evidence = aggregate_qualification_evidence([_operation()], "a" * 40, required_subject_ids={"q01-sim004-success-time", "q01-sim004-blocked-time"})
    assert evidence["task_specific_result"] == "SIM_PROVENANCE_QUALIFICATION_BLOCKED"
    json_path, report_path = write_qualification_artifacts(evidence, tmp_path / "evidence.json", tmp_path / "report.md")
    assert json.loads(json_path.read_text()) == evidence
    assert "SIM_PROVENANCE_QUALIFICATION_BLOCKED" in report_path.read_text()
    assert render_qualification_report(evidence) == report_path.read_text()


def test_gazebo_sidecar_accepts_only_structured_stats_json() -> None:
    assert read_gazebo_simulation_time('{"simTime":{"sec":2,"nsec":3}}') == {"source": "gz_stats", "seconds": 2.000000003}
    with pytest.raises(ValueError, match="MISSING_STRUCTURED_SIMULATION_TIME"):
        read_gazebo_simulation_time('sim time=2')


def test_sim004_sidecar_uses_accepted_runtime_transport_partition(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}
    class Completed:
        returncode = 0
        stdout = '{"simTime":{"sec":2,"nsec":3}}'
    def run(command: list[str], **kwargs: object) -> Completed:
        captured["command"] = command
        captured["env"] = kwargs["env"]
        captured["timeout"] = kwargs["timeout"]
        return Completed()
    monkeypatch.setattr("scripts.q01_execution_adapters.subprocess.run", run)
    runtime = type("Runtime", (), {"environment": {"GZ_PARTITION": "q01-test"}})()
    assert gazebo_clock(runtime, "sim004_navigation_proxy_world") == {"simTime": {"sec": 2, "nsec": 3}}
    assert captured["command"][-1] == "/world/sim004_navigation_proxy_world/stats"
    assert captured["env"] == {"GZ_PARTITION": "q01-test"}
    assert captured["timeout"] == 15


def test_sim009_gazebo_stats_timeout_becomes_missing_run_local_observation(monkeypatch: pytest.MonkeyPatch) -> None:
    runtime = type("Runtime", (), {"environment": {"GZ_PARTITION": "q01-test"}})()

    def timed_out(*_args: object, **_kwargs: object) -> None:
        raise subprocess.TimeoutExpired(["gz", "topic"], 5)

    monkeypatch.setattr("scripts.q01_execution_adapters.subprocess.run", timed_out)
    with pytest.raises(RuntimeError, match="Gazebo stats sidecar"):
        gazebo_clock(runtime, "sim004_navigation_proxy_world")
    assert _sim009_sidecar_observation({"backend": "gazebo_navigation"}, {}, runtime) is None


def test_sim009_sidecar_retries_transient_stats_discovery_for_same_scenario(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime = type("Runtime", (), {"environment": {"GZ_PARTITION": "q01-same-run"}})()
    observations: list[str] = []

    def transient_clock(observed_runtime: object, world_name: str) -> dict[str, object]:
        assert observed_runtime is runtime
        assert world_name == "sim004_navigation_proxy_world"
        observations.append(world_name)
        if len(observations) == 1:
            raise RuntimeError("Gazebo stats sidecar timed out")
        return {"simTime": {"sec": 7, "nsec": 250_000_000}}

    monkeypatch.setattr("scripts.q01_execution_adapters.gazebo_clock", transient_clock)
    observation = _sim009_sidecar_observation(
        {"backend": "gazebo_navigation", "id": "SIM009-NAV-BLOCKED"},
        {"pass": True},
        runtime,
    )

    assert len(observations) == 2
    assert observation is not None
    assert observation["simulation_time"] == {"source": "gz_stats", "seconds": 7.25}


def test_sim009_unknown_reconciliation_retains_real_mujoco_simulation_time() -> None:
    from simulation_runtime.failure_recovery import _vla_scenario, load_manifest

    scenario = next(
        row for row in load_manifest()["scenarios"]
        if row["id"] == "SIM009-VLA-UNKNOWN"
    )
    row = _vla_scenario(scenario)

    observation = _sim009_sidecar_observation(scenario, row, None)

    assert row["result"]["status"] == "unknown"
    assert row["reconciliation"]["observed_status"] == "succeeded"
    assert row["measurement"]["scenario"] == "mujoco-unknown"
    assert observation is not None
    assert observation["simulation_time"] == {
        "source": "mujoco_steps_times_timestep",
        "seconds": 0.8,
    }


def test_sim004_actual_result_converts_to_subject_without_historical_time_backfill() -> None:
    template = _operation(qualification_run_id="q01-sim004-success-time")
    subject = collect_sim004_execution_result(template, {
        "qualification_run_id": "q01-sim004-success-time",
        "scenario_id": "success",
        "simulation_time": {"source": "gz_stats", "seconds": 2.0},
        "wall_time_ms": 12.0,
        "world_sha256": "e" * 64,
        "bridge_sha256": "c" * 64,
        "launch_sha256": "d" * 64,
        "cleanup_complete": True,
        "semantic_outcome": {"result": "success"},
    })
    assert subject.timing == {"simulation_time": 2.0, "simulation_time_source": "gz_stats", "wall_time_ms": 12.0, "bounded_execution": True}
    with pytest.raises(ValueError, match="MISSING_STRUCTURED_SIMULATION_TIME"):
        collect_sim004_execution_result(template, {"wall_time_ms": 12.0})


def test_sim004_live_supplier_reuses_sidecar_execution_for_every_required_scenario() -> None:
    """The canonical live supplier, rather than manifest data, supplies new-run facts."""
    from simulation_runtime.navigation_backend import RuntimeObservation

    class ControlledRuntime:
        environment = {"GZ_PARTITION": "q01-controlled"}
        world_path = ROOT / "data/simulation/sim004_navigation_proxy_world.sdf"

        def __init__(self) -> None:
            self.started = False
            self.closed = False
            self.observations: dict[str, RuntimeObservation] = {}

        @property
        def ready(self) -> bool:
            return self.started

        def start(self) -> None:
            self.started = True

        def bootstrap_localization(self) -> bool:
            return True

        def navigate(self, request: dict[str, object]) -> RuntimeObservation:
            if request["destination_id"] == "blocked-bay":
                observation = RuntimeObservation("failed", error_code="NAVIGATION_ABORTED")
            elif request["timeout_ms"] == 1:
                observation = RuntimeObservation("unknown", error_code="NAVIGATION_TIMEOUT", retryable=True)
            else:
                observation = RuntimeObservation("succeeded", arrival_verified=True)
            self.observations[str(request["action_id"])] = observation
            return observation

        def reconcile(self, action_id: str) -> RuntimeObservation:
            return self.observations[action_id]

        def close(self) -> bool:
            self.closed = True
            return True

    run_ids = {
        "success": "q01-sim004-success-time",
        "blocked": "q01-sim004-blocked-time",
        "timeout_reconciliation": "q01-sim004-timeout-reconciliation-time",
    }
    for scenario_id, run_id in run_ids.items():
        supplier = getattr(q01_execution_adapters, "run_sim004_qualification", None)
        assert callable(supplier), "SIM-004 live supplier must compose the accepted runtime sidecar"
        raw = supplier(
            scenario_id,
            runtime_factory=ControlledRuntime,
            clock_probe=lambda _runtime, _world: {"simTime": {"sec": 2, "nsec": 3}},
        )
        subject = collect_sim004_execution_result(
            _operation(qualification_run_id=run_id, scenario_id=scenario_id), raw,
        )
        assert subject.qualification_run_id == run_id
        assert subject.timing["simulation_time_source"] == "gz_stats"
        assert raw["cleanup_complete"] is True
        assert raw["world_sha256"] != raw["bridge_sha256"]
        assert raw["semantic_outcome"]["result"] in {"success", "failure", "pending"}


def test_live_adapter_map_dispatches_only_min_q01_tasks() -> None:

    def sim008_supplier() -> dict[str, object]:
        return {"qualification_run_id": "q01-sim008-normal-system-authority"}

    def sim009_supplier() -> dict[str, object]:
        return {"SIM009-VLA-GRASP-MISS": {"scenario_id": "SIM009-VLA-GRASP-MISS"}}

    adapter_factory = getattr(run_simulation_provenance_qualification, "live_adapters", None)
    assert callable(adapter_factory), "canonical runner must expose its live adapter dispatcher"
    adapters = adapter_factory(sim008_supplier=sim008_supplier, sim009_supplier=sim009_supplier)
    assert adapters == {
        "TASK-SIM-008": sim008_supplier,
        "TASK-SIM-009": sim009_supplier,
    }
    assert adapters["TASK-SIM-008"]() == {"qualification_run_id": "q01-sim008-normal-system-authority"}
    assert adapters["TASK-SIM-009"]()["SIM009-VLA-GRASP-MISS"] == {"scenario_id": "SIM009-VLA-GRASP-MISS"}


def test_canonical_routing_excludes_sim004_supplier() -> None:
    bindings = {}
    for short, evidence in (("SIM-004", "navigation_backend"), ("SIM-005", "mujoco_vla_backend"), ("SIM-007", "mission_integration"), ("SIM-008", "normal_system_e2e"), ("SIM-009", "failure_recovery")):
        acceptance = json.loads((ROOT / f"results/reviews/{short}_acceptance.json").read_text())
        bindings[f"TASK-{short}"] = resolve_predecessor_binding(ROOT, f"TASK-{short}", acceptance, f"results/simulation/{short}_{evidence}.json")
    with pytest.raises(ValueError, match="MISSING_LIVE_QUALIFICATION_RESULT:SIM-008"):
        collect_qualification_subjects(
            bindings,
            run_simulation_provenance_qualification.live_adapters(sim008_supplier=lambda: None, sim009_supplier=lambda: None),
        )


def test_canonical_routing_excludes_sim005_supplier_without_importing_mujoco() -> None:
    bindings = {}
    for short, evidence in (("SIM-004", "navigation_backend"), ("SIM-005", "mujoco_vla_backend"), ("SIM-007", "mission_integration"), ("SIM-008", "normal_system_e2e"), ("SIM-009", "failure_recovery")):
        acceptance = json.loads((ROOT / f"results/reviews/{short}_acceptance.json").read_text())
        bindings[f"TASK-{short}"] = resolve_predecessor_binding(ROOT, f"TASK-{short}", acceptance, f"results/simulation/{short}_{evidence}.json")
    with pytest.raises(ValueError, match="MISSING_LIVE_QUALIFICATION_RESULT:SIM-008"):
        collect_qualification_subjects(
            bindings,
            run_simulation_provenance_qualification.live_adapters(sim008_supplier=lambda: None, sim009_supplier=lambda: None),
        )


def test_canonical_routing_collects_sim008_from_its_live_supplier_without_authority_reconstruction() -> None:
    bindings = {}
    for short, evidence in (("SIM-004", "navigation_backend"), ("SIM-005", "mujoco_vla_backend"), ("SIM-007", "mission_integration"), ("SIM-008", "normal_system_e2e"), ("SIM-009", "failure_recovery")):
        acceptance = json.loads((ROOT / f"results/reviews/{short}_acceptance.json").read_text())
        bindings[f"TASK-{short}"] = resolve_predecessor_binding(ROOT, f"TASK-{short}", acceptance, f"results/simulation/{short}_{evidence}.json")
    raw = run_sim008_qualification(lambda: {
        "mission": {"mission_id": "m-008", "request_id": "r-008", "trace_id": "t-008", "component_version": "sim008-normal-system-e2e-v1", "result": "success", "status": "succeeded"},
        "lifecycle": {"startup_attempted": True, "cleanup_complete": True},
        "steps": [{"result": {"simulation_time": {"sec": 3, "nsec": 0}}}],
    })
    with pytest.raises(ValueError, match="MISSING_LIVE_QUALIFICATION_RESULT:SIM009-NAV-BLOCKED"):
        collect_qualification_subjects(
            bindings,
            run_simulation_provenance_qualification.live_adapters(
                sim008_supplier=lambda: raw,
                sim009_supplier=lambda: None,
            ),
        )


def test_canonical_routing_collects_sim009_by_explicit_scenario_without_backfill() -> None:
    bindings = {}
    for short, evidence in (("SIM-004", "navigation_backend"), ("SIM-005", "mujoco_vla_backend"), ("SIM-007", "mission_integration"), ("SIM-008", "normal_system_e2e"), ("SIM-009", "failure_recovery")):
        acceptance = json.loads((ROOT / f"results/reviews/{short}_acceptance.json").read_text())
        bindings[f"TASK-{short}"] = resolve_predecessor_binding(ROOT, f"TASK-{short}", acceptance, f"results/simulation/{short}_{evidence}.json")
    records = run_sim009_qualification(lambda: {"scenarios": [{
        "id": "SIM009-VLA-GRASP-MISS", "backend": "mujoco", "decision": "FAIL_CLOSED", "outcome_kind": "failure", "cleanup_complete": True,
        "result": {"mission_id": "m-009", "request_id": "r-009", "trace_id": "t-009", "action_id": "a-009", "component_version": "sim005-mujoco-vla-backend-v1", "result": "failure", "status": "failed"},
        "qualification_observation": {"simulation_time": {"source": "mujoco_steps_times_timestep", "seconds": 0.8}, "configuration_sha256": "a" * 64, "world_model_sha256": "b" * 64, "source_paths": {"configuration": "configs/simulation/sim005_mujoco_manipulation.yaml", "world_model": "data/simulation/sim005_mujoco_manipulation.xml"}},
    }]})
    with pytest.raises(ValueError, match="MISSING_LIVE_QUALIFICATION_RESULT:SIM-008"):
        collect_qualification_subjects(
            bindings,
            run_simulation_provenance_qualification.live_adapters(
                sim008_supplier=lambda: None,
                sim009_supplier=lambda: records,
            ),
        )


def test_sim005_wrapper_creates_new_identity_and_extracts_same_run_measurement() -> None:
    pytest.importorskip("mujoco")
    record = run_sim005_qualification("mujoco-place-nominal")
    assert record["qualification_run_id"].startswith("q01-sim005-")
    assert record["new_run"] is True
    assert set(record["correlation_identity"]) == {"mission_id", "request_id", "trace_id", "action_id"}
    assert record["measurement"]["scenario"] == "mujoco-place-nominal"
    assert record["provenance"]["mujoco_version"] == "3.13.0"


def test_sim005_actual_result_converts_to_subject_with_same_run_provenance() -> None:
    pytest.importorskip("mujoco")
    raw = run_sim005_qualification("mujoco-place-nominal")
    template = _operation(
        subject_id="q01-sim005-mujoco-place-nominal",
        predecessor_binding={"task_id": "TASK-SIM-005", "accepted_commit": "a" * 40, "evidence_path": "results/simulation/SIM-005_mujoco_vla_backend.json", "evidence_sha256": "b" * 64},
        backend_id="mujoco",
        scenario_id="mujoco-place-nominal",
    )
    subject = collect_sim005_execution_result(template, raw)
    assert subject.correlation_identity == raw["correlation_identity"]
    assert subject.semantic_outcome == raw["semantic_outcome"]
    assert subject.qualification_run_id == raw["qualification_run_id"]
    assert subject.timing["simulation_time_source"] == "mujoco_steps_times_timestep"
    assert subject.timing["mujoco_version"] == raw["provenance"]["mujoco_version"]
    assert subject.timing["seed"] == raw["provenance"]["seed"]
    assert subject.timing["initial_state_id"] == raw["provenance"]["initial_state_id"]
    assert set(subject.configuration_provenance) == {"execution_configuration", "backend_source"}
    assert set(subject.world_model_provenance) == {"model", "initial_state"}
    assert subject.authority_paths["model"] == "data/simulation/sim005_mujoco_manipulation.xml"
    with pytest.raises(ValueError, match="MISSING_RUN_LOCAL_PROVENANCE"):
        collect_sim005_execution_result(template, {**raw, "provenance": {}})
    with pytest.raises(ValueError, match="CROSS_SCENARIO_ASSOCIATION"):
        collect_sim005_execution_result(template, {**raw, "measurement": {**raw["measurement"], "scenario": "mujoco-grasp-miss"}})
    with pytest.raises(ValueError, match="HISTORICAL_TRACE_INJECTION"):
        collect_sim005_execution_result(template, {**raw, "new_run": False})


def test_sim008_wrapper_preserves_execution_and_structured_world_time() -> None:
    outcome = {"mission": {"mission_id": "m-1", "request_id": "r-1", "trace_id": "t-1", "component_version": "sim008-normal-system-e2e-v1", "result": "failure"}, "lifecycle": {"startup_attempted": True, "cleanup_complete": False}, "steps": [{"result": {"simulation_time": {"sec": 4, "nsec": 0}}}]}
    record = run_sim008_qualification(lambda: outcome)
    assert record["qualification_run_id"] == "q01-sim008-normal-system-authority"
    assert record["semantic_outcome"] == {"result": "failure"}
    assert record["cleanup_complete"] is False
    assert record["simulation_time"] == {"source": "gazebo_authoritative_observation", "seconds": 4.0, "raw": {"sec": 4, "nsec": 0}}
    assert record["correlation_identity"] == {"mission_id": "m-1", "request_id": "r-1", "trace_id": "t-1"}
    assert record["execution_authority"]["bridge_sha256"] != record["execution_authority"]["launch_sha256"]


def test_sim008_actual_result_converts_to_subject_with_execution_bound_authority() -> None:
    raw = run_sim008_qualification(lambda: {
        "mission": {"mission_id": "m-1", "request_id": "r-1", "trace_id": "t-1", "component_version": "sim008-normal-system-e2e-v1", "result": "failure"},
        "lifecycle": {"startup_attempted": True, "cleanup_complete": False},
        "steps": [{"result": {"simulation_time": {"sec": 4, "nsec": 0}}}],
    })
    template = _operation(
        subject_id="q01-sim008-normal-system-authority",
        predecessor_binding={"task_id": "TASK-SIM-008", "accepted_commit": "a" * 40, "evidence_path": "results/simulation/SIM-008_normal_system_e2e.json", "evidence_sha256": "b" * 64},
        qualification_run_id="q01-sim008-normal-system-authority",
        scenario_id=raw["scenario_id"],
        backend_id="gazebo",
    )
    subject = collect_sim008_execution_result(template, raw)
    assert subject.correlation_identity == raw["correlation_identity"]
    assert subject.semantic_outcome == raw["semantic_outcome"]
    assert subject.configuration_provenance["bridge_configuration"] != subject.configuration_provenance["launch_run_configuration"]
    assert subject.world_model_provenance["world"] == raw["execution_authority"]["world_sha256"]
    assert subject.timing["simulation_time_source"] == "gazebo_authoritative_observation"
    with pytest.raises(ValueError, match="MISSING_RUN_LOCAL_PROVENANCE"):
        collect_sim008_execution_result(template, {**raw, "execution_authority": {}})
    with pytest.raises(ValueError, match="MISSING_STRUCTURED_SIMULATION_TIME"):
        collect_sim008_execution_result(template, {**raw, "simulation_time": {"source": "wall", "seconds": 4.0}})


def test_sim009_wrapper_binds_rows_by_explicit_scenario_id_and_preserves_failure() -> None:
    suite = {"scenarios": [{"id": "SIM009-VLA-GRASP-MISS", "backend": "mujoco", "decision": "FAIL_CLOSED", "outcome_kind": "failure", "cleanup_complete": True,
        "qualification_attempt": {"qualification_run_id": "q01-sim009-attempt-1", "scenario_execution_id": "scenario-execution-1"},
        "result": {"mission_id": "m-1", "request_id": "r-1", "trace_id": "t-1", "action_id": "a-1", "component_version": "sim005-mujoco-vla-backend-v1", "result": "failure", "status": "failed"},
        "qualification_observation": {"simulation_time": {"source": "mujoco_steps_times_timestep", "seconds": 0.8}, "configuration_sha256": "a" * 64, "world_model_sha256": "b" * 64, "source_paths": {"configuration": "configs/simulation/sim005_mujoco_manipulation.yaml", "world_model": "data/simulation/sim005_mujoco_manipulation.xml"}}}]}
    records = run_sim009_qualification(lambda: suite)
    assert records["SIM009-VLA-GRASP-MISS"]["qualification_run_id"] == "q01-sim009-attempt-1"
    assert records["SIM009-VLA-GRASP-MISS"]["execution_identity"]["scenario_execution_id"] == "scenario-execution-1"
    assert records["SIM009-VLA-GRASP-MISS"]["semantic_outcome"]["outcome_kind"] == "failure"
    assert records["SIM009-VLA-GRASP-MISS"]["run_local_provenance"]["simulation_time"]["seconds"] == 0.8
    with pytest.raises(ValueError, match="DUPLICATE_SCENARIO_ID"):
        run_sim009_qualification(lambda: {"scenarios": suite["scenarios"] * 2})


def test_sim009_timeout_wrapper_preserves_reconciliation_retry_and_identity_semantics() -> None:
    reconciliation = {"result": "success", "observed_status": "failed", "action_id": "a-009"}
    authorization = {"reconciliation_completed": True, "resolved_status": "failed", "error": {"retryable": True}}
    suite = {"scenarios": [{
        "id": "SIM009-NAV-TIMEOUT-RETRY", "backend": "gazebo_navigation", "decision": "RETRY", "outcome_kind": "unknown", "cleanup_complete": True,
        "first_result": {"mission_id": "m-009", "request_id": "r-009", "trace_id": "t-009", "action_id": "a-009", "component_version": "sim009-failure-suite-v1", "result": "pending", "status": "unknown"},
        "reconciliation": reconciliation, "retry_authorization": authorization,
        "retry_request": {"request_id": "r-010", "action_id": "a-009"}, "retry_result": {"result": "success", "status": "succeeded"},
        "identity": {"action_id_stable": True, "retry_request_id_new": True}, "logical_side_effect_count": 1,
    }]}
    record = run_sim009_qualification(lambda: suite)["SIM009-NAV-TIMEOUT-RETRY"]
    assert record["semantic_outcome"]["reconciliation"] == reconciliation
    assert record["semantic_outcome"]["retry_authorization"] == authorization
    assert record["semantic_outcome"]["retry_request"]["action_id"] == "a-009"
    assert record["semantic_outcome"]["identity"]["action_id_stable"] is True


def test_sim009_actual_result_converts_to_subject_without_cross_scenario_backfill() -> None:
    records = run_sim009_qualification(lambda: {"scenarios": [{"id": "SIM009-VLA-GRASP-MISS", "backend": "mujoco", "decision": "FAIL_CLOSED", "outcome_kind": "failure", "cleanup_complete": True,
        "result": {"mission_id": "m-1", "request_id": "r-1", "trace_id": "t-1", "action_id": "a-1", "component_version": "sim005-mujoco-vla-backend-v1", "result": "failure", "status": "failed"},
        "qualification_observation": {"simulation_time": {"source": "mujoco_steps_times_timestep", "seconds": 0.8}, "configuration_sha256": "a" * 64, "world_model_sha256": "b" * 64, "source_paths": {"configuration": "configs/simulation/sim005_mujoco_manipulation.yaml", "world_model": "data/simulation/sim005_mujoco_manipulation.xml"}}}]})
    raw = records["SIM009-VLA-GRASP-MISS"]
    template = _operation(
        subject_id="q01-sim009-SIM009-VLA-GRASP-MISS",
        predecessor_binding={"task_id": "TASK-SIM-009", "accepted_commit": "a" * 40, "evidence_path": "results/simulation/SIM-009_failure_recovery.json", "evidence_sha256": "b" * 64},
        qualification_run_id=raw["qualification_run_id"], scenario_id="SIM009-VLA-GRASP-MISS", backend_id="mujoco",
    )
    subject = collect_sim009_execution_result(template, raw)
    assert subject.correlation_identity == raw["correlation_identity"]
    assert subject.semantic_outcome["outcome_kind"] == "failure"
    assert subject.timing["simulation_time_source"] == "mujoco_steps_times_timestep"
    with pytest.raises(ValueError, match="CROSS_SCENARIO_ASSOCIATION"):
        collect_sim009_execution_result(template, {**raw, "scenario_id": "SIM009-VLA-CONTACT-LOSS"})
    with pytest.raises(ValueError, match="MISSING_RUN_LOCAL_PROVENANCE"):
        collect_sim009_execution_result(template, {**raw, "run_local_provenance": {}})


def test_canonical_manifest_is_exactly_the_frozen_min_q01_subject_set() -> None:
    manifest = required_subject_manifest()
    assert len(manifest) == 11
    assert manifest.count("q01-sim008-normal-system-authority") == 1
    assert "q01-sim009-SIM009-NAV-BLOCKED" in manifest
    assert not any(subject.startswith(("q01-sim004-", "q01-sim005-", "q01-sim007-")) for subject in manifest)


def test_canonical_routing_does_not_start_excluded_sim005_runtime() -> None:
    bindings = {}
    for short, evidence in (("SIM-004", "navigation_backend"), ("SIM-005", "mujoco_vla_backend"), ("SIM-007", "mission_integration"), ("SIM-008", "normal_system_e2e"), ("SIM-009", "failure_recovery")):
        acceptance = json.loads((ROOT / f"results/reviews/{short}_acceptance.json").read_text())
        bindings[f"TASK-{short}"] = resolve_predecessor_binding(ROOT, f"TASK-{short}", acceptance, f"results/simulation/{short}_{evidence}.json")
    with pytest.raises(ValueError, match="MISSING_LIVE_SUPPLIER:TASK-SIM-008"):
        collect_qualification_subjects(bindings, {"TASK-SIM-005": lambda _scenario: (_ for _ in ()).throw(AssertionError("excluded supplier called"))})


def test_canonical_routing_invokes_each_live_supplier_once(monkeypatch) -> None:
    bindings = {}
    for short, evidence in (("SIM-008", "normal_system_e2e"), ("SIM-009", "failure_recovery")):
        acceptance = json.loads((ROOT / f"results/reviews/{short}_acceptance.json").read_text())
        bindings[f"TASK-{short}"] = resolve_predecessor_binding(
            ROOT, f"TASK-{short}", acceptance, f"results/simulation/{short}_{evidence}.json",
        )
    calls = {"sim008": 0, "sim009": 0}
    required_sim009 = [
        item.removeprefix("q01-sim009-")
        for item in required_subject_manifest(bindings) if item.startswith("q01-sim009-")
    ]

    def sim008():
        calls["sim008"] += 1
        return {"kind": "sim008"}

    def sim009():
        calls["sim009"] += 1
        return {scenario_id: {"scenario_id": scenario_id} for scenario_id in required_sim009}

    monkeypatch.setattr(
        run_simulation_provenance_qualification, "collect_sim008_execution_result",
        lambda template, _raw: template,
    )
    monkeypatch.setattr(
        run_simulation_provenance_qualification, "collect_sim009_execution_result",
        lambda template, raw: template if raw["scenario_id"] == template.scenario_id else (_ for _ in ()).throw(ValueError("CROSS_SCENARIO_ASSOCIATION")),
    )

    subjects = collect_qualification_subjects(
        bindings, {"TASK-SIM-008": sim008, "TASK-SIM-009": sim009},
    )

    assert calls == {"sim008": 1, "sim009": 1}
    assert len(subjects) == 11


def test_canonical_runner_imports_live_adapters_when_invoked_as_a_script(tmp_path: Path) -> None:
    completed = subprocess.run(
        [sys.executable, "scripts/run_simulation_provenance_qualification.py", "--help"],
        cwd=ROOT, text=True, capture_output=True,
    )
    assert completed.returncode == 0
    assert "No module named 'scripts'" not in completed.stderr
