"""Fail-closed models for additive simulation provenance qualification."""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
import re
import subprocess
from typing import Any, Mapping

RECORD_KINDS = frozenset({"operation_run", "profile_aggregate", "version_qualification"})
_FAKE = frozenset({"", "not_applicable", "N/A", "unknown", "placeholder"})


@dataclass(frozen=True)
class QualificationSubject:
    subject_id: str
    record_kind: str
    claim_scope: str
    predecessor_binding: Mapping[str, Any]
    qualification_run_id: str | None
    scenario_id: str | None
    backend_id: str
    component_version: str
    configuration_provenance: Mapping[str, str]
    world_model_provenance: Mapping[str, str]
    timing: Mapping[str, Any] | None
    semantic_outcome: Mapping[str, Any] | None
    profile_id: str | None = None
    correlation_identity: Mapping[str, str] | None = None
    authority_paths: Mapping[str, str] | None = None


@dataclass(frozen=True)
class VerifiedPredecessorBinding:
    task_id: str
    accepted_commit: str
    evidence_path: str
    evidence_sha256: str
    evidence: Mapping[str, Any]


def resolve_predecessor_binding(root: Path, task_id: str, acceptance: Mapping[str, Any], evidence_path: str) -> VerifiedPredecessorBinding:
    """Resolve a canonical Evidence object from its immutable accepted tree."""
    if acceptance.get("task_id") != task_id or acceptance.get("status") != "ACCEPT":
        raise ValueError("ACCEPTANCE_IDENTITY_MISMATCH")
    commit = acceptance.get("accepted_commit")
    if not isinstance(commit, str) or len(commit) != 40:
        raise ValueError("INVALID_ACCEPTED_COMMIT")
    exists = subprocess.run(["git", "cat-file", "-e", f"{commit}^{{commit}}"], cwd=root, capture_output=True)
    if exists.returncode:
        raise ValueError("INVALID_ACCEPTED_COMMIT")
    blob = subprocess.run(["git", "show", f"{commit}:{evidence_path}"], cwd=root, capture_output=True)
    if blob.returncode:
        raise ValueError("MISSING_ACCEPTED_EVIDENCE")
    digest = hashlib.sha256(blob.stdout).hexdigest()
    try:
        evidence = json.loads(blob.stdout)
    except json.JSONDecodeError as exc:
        raise ValueError("MALFORMED_ACCEPTED_EVIDENCE") from exc
    if not isinstance(evidence, dict) or evidence.get("task_id") != task_id:
        raise ValueError("TASK_ID_MISMATCH")
    return VerifiedPredecessorBinding(task_id, commit, evidence_path, digest, evidence)


def build_gazebo_subject(template: QualificationSubject, measurement: Mapping[str, Any]) -> QualificationSubject:
    """Bind only a structured simulator measurement; logs never supply time."""
    simulation_time = measurement.get("simulation_time")
    if not isinstance(simulation_time, (int, float)):
        raise ValueError("MISSING_STRUCTURED_SIMULATION_TIME")
    timing = dict(template.timing or {})
    timing["simulation_time"] = simulation_time
    if "wall_time_ms" in measurement:
        timing["wall_time_ms"] = measurement["wall_time_ms"]
    subject = QualificationSubject(**{**template.__dict__, "timing": timing})
    validate_subject(subject)
    return subject


def collect_sim004_execution_result(template: QualificationSubject, result: Mapping[str, Any]) -> QualificationSubject:
    """Convert one new sidecar-observed SIM-004 run without historical backfill."""
    clock = result.get("simulation_time")
    if not isinstance(clock, Mapping) or clock.get("source") != "gz_stats" or not isinstance(clock.get("seconds"), (int, float)):
        raise ValueError("MISSING_STRUCTURED_SIMULATION_TIME")
    for field in ("world_sha256", "bridge_sha256", "launch_sha256"):
        if not isinstance(result.get(field), str) or len(result[field]) != 64:
            raise ValueError("MISSING_EXECUTION_ASSET_BINDING")
    if result.get("scenario_id") != template.scenario_id or result.get("qualification_run_id") != template.qualification_run_id:
        raise ValueError("CROSS_SCENARIO_ASSOCIATION")
    outcome = result.get("semantic_outcome")
    if not isinstance(outcome, Mapping) or result.get("cleanup_complete") is not True:
        raise ValueError("INVALID_EXECUTION_RESULT")
    subject = QualificationSubject(**{**template.__dict__,
        "configuration_provenance": {"bridge": result["bridge_sha256"], "launch": result["launch_sha256"]},
        "world_model_provenance": {"world": result["world_sha256"]},
        "timing": {"simulation_time": clock["seconds"], "simulation_time_source": clock["source"], "wall_time_ms": result.get("wall_time_ms"), "bounded_execution": True},
        "semantic_outcome": outcome,
    })
    validate_subject(subject)
    return subject


def build_mujoco_subject(template: QualificationSubject, run: Mapping[str, Any]) -> QualificationSubject:
    """Attach correlation only to a newly created Q01 MuJoCo qualification run."""
    if run.get("new_run") is not True:
        raise ValueError("HISTORICAL_TRACE_INJECTION")
    trace_id = run.get("trace_id")
    if not isinstance(trace_id, str) or trace_id in _FAKE:
        raise ValueError("MISSING_TRACE_ID")
    for field in ("mission_id", "request_id"):
        if not isinstance(run.get(field), str) or run[field] in _FAKE:
            raise ValueError(f"MISSING_{field.upper()}")
    subject = QualificationSubject(**{**template.__dict__, "correlation_identity": {key: value for key, value in run.items() if key in {"mission_id", "request_id", "trace_id", "action_id"}}})
    return subject


def collect_sim005_execution_result(template: QualificationSubject, result: Mapping[str, Any]) -> QualificationSubject:
    """Normalize one new MuJoCo wrapper result without historical run-local backfill."""
    if template.predecessor_binding.get("task_id") != "TASK-SIM-005":
        raise ValueError("PREDECESSOR_TASK_MISMATCH")
    qualification_run_id = result.get("qualification_run_id")
    if not isinstance(qualification_run_id, str) or not qualification_run_id.startswith("q01-sim005-"):
        raise ValueError("INVALID_QUALIFICATION_RUN_ID")
    correlation = result.get("correlation_identity")
    measurement = result.get("measurement")
    provenance = result.get("provenance")
    outcome = result.get("semantic_outcome")
    if not all(isinstance(value, Mapping) for value in (correlation, measurement, provenance, outcome)):
        raise ValueError("MISSING_RUN_LOCAL_PROVENANCE")
    if measurement.get("scenario") != template.scenario_id:
        raise ValueError("CROSS_SCENARIO_ASSOCIATION")
    if result.get("new_run") is not True:
        raise ValueError("HISTORICAL_TRACE_INJECTION")
    assets = provenance.get("assets")
    if not isinstance(assets, list):
        raise ValueError("MISSING_RUN_LOCAL_PROVENANCE")
    asset_hashes = {
        str(asset.get("path")): asset.get("sha256")
        for asset in assets
        if isinstance(asset, Mapping) and isinstance(asset.get("path"), str) and isinstance(asset.get("sha256"), str)
    }
    config_hash = asset_hashes.get("configs/simulation/sim005_mujoco_manipulation.yaml")
    model_hash = asset_hashes.get("data/simulation/sim005_mujoco_manipulation.xml")
    backend_hash = asset_hashes.get("src/simulation_runtime/mujoco_vla_backend.py")
    if not all(isinstance(value, str) and len(value) == 64 for value in (config_hash, model_hash, backend_hash)):
        raise ValueError("MISSING_RUN_LOCAL_PROVENANCE")
    if not isinstance(provenance.get("mujoco_version"), str) or not isinstance(provenance.get("backend_id"), str):
        raise ValueError("MISSING_RUNTIME_PROVENANCE")
    if not isinstance(provenance.get("initial_state_id"), str) or not isinstance(provenance.get("seed"), int):
        raise ValueError("MISSING_INITIAL_STATE_PROVENANCE")
    steps, timestep = measurement.get("steps"), measurement.get("timestep_seconds")
    if not isinstance(steps, int) or not isinstance(timestep, (int, float)):
        raise ValueError("MISSING_STRUCTURED_SIMULATION_TIME")
    base = QualificationSubject(**{**template.__dict__,
        "qualification_run_id": qualification_run_id,
        "component_version": provenance["backend_id"],
        "configuration_provenance": {"execution_configuration": config_hash, "backend_source": backend_hash},
        "world_model_provenance": {
            "model": model_hash,
            "initial_state": _canonical_sha256({"initial_state_id": provenance["initial_state_id"], "seed": provenance["seed"]}),
        },
        "timing": {
            "simulation_time": steps * timestep,
            "simulation_time_source": "mujoco_steps_times_timestep",
            "steps": steps,
            "timestep_seconds": timestep,
            "mujoco_version": provenance["mujoco_version"],
            "seed": provenance["seed"],
            "initial_state_id": provenance["initial_state_id"],
            "bounded_execution": True,
        },
        "semantic_outcome": dict(outcome),
        "authority_paths": {
            "execution_configuration": "configs/simulation/sim005_mujoco_manipulation.yaml",
            "model": "data/simulation/sim005_mujoco_manipulation.xml",
            "backend_source": "src/simulation_runtime/mujoco_vla_backend.py",
        },
    })
    subject = build_mujoco_subject(base, {"new_run": True, **correlation})
    validate_subject(subject)
    return subject


def _canonical_sha256(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def read_gazebo_simulation_time(stats_json: str) -> dict[str, Any]:
    """Decode only Gazebo's structured stats response; never parse log prose."""
    try:
        stats = json.loads(stats_json)
        value = stats["simTime"]
        seconds = int(value["sec"]) + int(value.get("nsec", 0)) / 1_000_000_000
    except (TypeError, ValueError, KeyError, json.JSONDecodeError) as exc:
        raise ValueError("MISSING_STRUCTURED_SIMULATION_TIME") from exc
    return {"source": "gz_stats", "seconds": seconds}


def _accepted_blob(root: Path, commit: str, path: str) -> bytes:
    blob = subprocess.run(["git", "show", f"{commit}:{path}"], cwd=root, capture_output=True)
    if blob.returncode:
        raise ValueError("MISSING_ACCEPTED_SOURCE")
    return blob.stdout


def collect_sim007_profile_qualifications(
    root: Path, binding: VerifiedPredecessorBinding,
) -> list[QualificationSubject]:
    """Qualify frozen SIM-007 aggregate profiles without inventing operation IDs."""
    if binding.task_id != "TASK-SIM-007":
        raise ValueError("PREDECESSOR_TASK_MISMATCH")
    evidence = binding.evidence
    profiles = evidence.get("profiles")
    smoke = evidence.get("profile_smoke")
    if not isinstance(profiles, Mapping) or not isinstance(smoke, list):
        raise ValueError("MALFORMED_SIM007_ACCEPTED_EVIDENCE")
    source_path = "src/simulation_runtime/mission_integration.py"
    source = _accepted_blob(root, binding.accepted_commit, source_path).decode()
    version_match = re.search(r'^COMPONENT_VERSION = "([^"]+)"$', source, re.MULTILINE)
    if version_match is None:
        raise ValueError("MISSING_SIM007_COMPONENT_VERSION")
    rows = {row.get("profile"): row for row in smoke if isinstance(row, Mapping)}
    expected = ("deterministic", "navigation_physics", "manipulation_physics", "system")
    if set(rows) != set(expected) or any(not isinstance(profiles.get(profile), Mapping) for profile in expected):
        raise ValueError("SIM007_PROFILE_SET_MISMATCH")
    predecessor_binding = {
        "task_id": binding.task_id,
        "accepted_commit": binding.accepted_commit,
        "evidence_path": binding.evidence_path,
        "evidence_sha256": binding.evidence_sha256,
    }
    subjects: list[QualificationSubject] = []
    for profile in expected:
        row = rows[profile]
        result = row.get("mission_result")
        failure_code = row.get("failure_code")
        if result not in {"success", "failure"} or (failure_code is not None and not isinstance(failure_code, str)):
            raise ValueError("INVALID_SIM007_AGGREGATE_OUTCOME")
        profile_source = profiles[profile]
        runtime_context = {
            "system_world": row.get("system_world"),
            "mujoco_live_world": row.get("mujoco_live_world"),
            "profile": profile,
        }
        subject = QualificationSubject(
            subject_id=f"q01-sim007-{profile}",
            record_kind="profile_aggregate",
            claim_scope="profile",
            predecessor_binding=predecessor_binding,
            qualification_run_id=None,
            scenario_id=None,
            backend_id=profile,
            component_version=version_match.group(1),
            configuration_provenance={"profile_source": _canonical_sha256({"profile": profile, "source": profile_source})},
            world_model_provenance={"profile_runtime_context": _canonical_sha256(runtime_context)},
            timing=None,
            semantic_outcome={"mission_result": result, "failure_code": failure_code},
            profile_id=profile,
            authority_paths={
                "profile_source": f"{binding.accepted_commit}:{binding.evidence_path}#/profiles/{profile}",
                "profile_runtime_context": f"{binding.accepted_commit}:{binding.evidence_path}#/profile_smoke/{expected.index(profile)}",
                "component_version": f"{binding.accepted_commit}:{source_path}",
            },
        )
        validate_subject(subject)
        subjects.append(subject)
    return subjects


def collect_sim008_configuration_qualification(root: Path, binding: VerifiedPredecessorBinding, measurement: Mapping[str, Any]) -> QualificationSubject:
    """Bind SIM-008 bridge and launch/run authorities as distinct frozen assets."""
    if binding.task_id != "TASK-SIM-008":
        raise ValueError("PREDECESSOR_TASK_MISMATCH")
    scenario = binding.evidence.get("scenario")
    execution = binding.evidence.get("execution")
    if not isinstance(scenario, Mapping) or not isinstance(execution, Mapping):
        raise ValueError("MALFORMED_SIM008_ACCEPTED_EVIDENCE")
    bridge_path = "src/simulation_runtime/normal_system_e2e.py"
    launch_path = "configs/simulation/sim008_normal_system_scenario.json"
    bridge_hash = hashlib.sha256(_accepted_blob(root, binding.accepted_commit, bridge_path)).hexdigest()
    launch_hash = hashlib.sha256(_accepted_blob(root, binding.accepted_commit, launch_path)).hexdigest()
    if bridge_hash == launch_hash:
        raise ValueError("SEMANTIC_HASH_ALIAS")
    component = execution.get("mission", {}).get("component_version") if isinstance(execution.get("mission"), Mapping) else None
    if not isinstance(component, str):
        raise ValueError("MISSING_SIM008_COMPONENT_VERSION")
    simulation_time = measurement.get("simulation_time")
    if not isinstance(simulation_time, (int, float)):
        raise ValueError("MISSING_STRUCTURED_SIMULATION_TIME")
    subject = QualificationSubject(
        subject_id="q01-sim008-normal-system-authority", record_kind="operation_run", claim_scope="run_local",
        predecessor_binding={"task_id": binding.task_id, "accepted_commit": binding.accepted_commit, "evidence_path": binding.evidence_path, "evidence_sha256": binding.evidence_sha256},
        qualification_run_id="q01-sim008-normal-system-authority", scenario_id=str(scenario.get("scenario_id")), backend_id="gazebo", component_version=component,
        configuration_provenance={"bridge_configuration": bridge_hash, "launch_run_configuration": launch_hash},
        world_model_provenance={"world": str(scenario.get("world_sha256"))},
        timing={"simulation_time": simulation_time, "bounded_execution": measurement.get("bounded_execution") is True}, semantic_outcome={"result": execution.get("mission", {}).get("result")},
        authority_paths={"bridge_configuration": f"{binding.accepted_commit}:{bridge_path}", "launch_run_configuration": f"{binding.accepted_commit}:{launch_path}"},
    )
    validate_subject(subject)
    return subject


def collect_sim008_execution_result(template: QualificationSubject, result: Mapping[str, Any]) -> QualificationSubject:
    """Normalize one new normal-E2E execution from its explicit execution bindings."""
    if template.predecessor_binding.get("task_id") != "TASK-SIM-008":
        raise ValueError("PREDECESSOR_TASK_MISMATCH")
    if result.get("qualification_run_id") != "q01-sim008-normal-system-authority" or result.get("qualification_run_id") != template.qualification_run_id:
        raise ValueError("INVALID_QUALIFICATION_RUN_ID")
    if result.get("scenario_id") != template.scenario_id or result.get("backend_id") != template.backend_id:
        raise ValueError("CROSS_SCENARIO_ASSOCIATION")
    authority = result.get("execution_authority")
    correlation = result.get("correlation_identity")
    timing = result.get("simulation_time")
    outcome = result.get("semantic_outcome")
    if not all(isinstance(value, Mapping) for value in (authority, correlation, timing, outcome)):
        raise ValueError("MISSING_RUN_LOCAL_PROVENANCE")
    if not all(isinstance(correlation.get(field), str) and correlation[field] for field in ("mission_id", "request_id", "trace_id")):
        raise ValueError("MISSING_RUN_LOCAL_CORRELATION")
    if timing.get("source") not in {"gazebo_authoritative_observation", "gz_stats"} or not isinstance(timing.get("seconds"), (int, float)):
        raise ValueError("MISSING_STRUCTURED_SIMULATION_TIME")
    hashes = {field: authority.get(field) for field in ("world_sha256", "system_sha256", "bridge_sha256", "launch_sha256")}
    if not all(isinstance(value, str) and len(value) == 64 for value in hashes.values()):
        raise ValueError("MISSING_RUN_LOCAL_PROVENANCE")
    if hashes["bridge_sha256"] == hashes["launch_sha256"]:
        raise ValueError("SEMANTIC_HASH_ALIAS")
    paths = authority.get("source_paths")
    if not isinstance(paths, Mapping) or not all(isinstance(paths.get(field), str) and paths[field] for field in ("world", "bridge_configuration", "launch_run_configuration")):
        raise ValueError("MISSING_EXECUTION_ASSET_BINDING")
    if not isinstance(result.get("component_version"), str) or not isinstance(result.get("startup_attempted"), bool) or not isinstance(result.get("cleanup_complete"), bool):
        raise ValueError("INVALID_EXECUTION_RESULT")
    subject = QualificationSubject(**{**template.__dict__,
        "component_version": result["component_version"],
        "configuration_provenance": {"bridge_configuration": hashes["bridge_sha256"], "launch_run_configuration": hashes["launch_sha256"]},
        "world_model_provenance": {"world": hashes["world_sha256"], "system": hashes["system_sha256"]},
        "timing": {
            "simulation_time": timing["seconds"],
            "simulation_time_source": timing["source"],
            "startup_attempted": result["startup_attempted"],
            "cleanup_complete": result["cleanup_complete"],
            "bounded_execution": True,
        },
        "semantic_outcome": dict(outcome),
        "correlation_identity": dict(correlation),
        "authority_paths": {
            "world": paths["world"],
            "bridge_configuration": paths["bridge_configuration"],
            "launch_run_configuration": paths["launch_run_configuration"],
        },
    })
    validate_subject(subject)
    return subject


def collect_sim009_scenario_qualifications(binding: VerifiedPredecessorBinding, measurements: Mapping[str, Mapping[str, Any]]) -> list[QualificationSubject]:
    """Require a distinct new measurement for every applicable SIM-009 physics scenario."""
    if binding.task_id != "TASK-SIM-009":
        raise ValueError("PREDECESSOR_TASK_MISMATCH")
    scenarios = binding.evidence.get("scenarios")
    if not isinstance(scenarios, list):
        raise ValueError("MALFORMED_SIM009_ACCEPTED_EVIDENCE")
    applicable = [row for row in scenarios if isinstance(row, Mapping) and row.get("backend") in {"gazebo_navigation", "mujoco"}]
    expected = {str(row.get("id")) for row in applicable}
    if set(measurements) != expected:
        raise ValueError("MISSING_SCENARIO_MEASUREMENT")
    subjects: list[QualificationSubject] = []
    for row in applicable:
        scenario_id = str(row["id"])
        measured = measurements[scenario_id]
        if measured.get("scenario_id") != scenario_id or measured.get("backend") != row.get("backend"):
            raise ValueError("CROSS_SCENARIO_ASSOCIATION")
        if not isinstance(measured.get("simulation_time"), (int, float)):
            raise ValueError("MISSING_STRUCTURED_SIMULATION_TIME")
        config, world = measured.get("configuration_sha256"), measured.get("world_model_sha256")
        if not all(isinstance(value, str) and len(value) == 64 for value in (config, world)):
            raise ValueError("MISSING_RUN_LOCAL_PROVENANCE")
        result = row.get("result") or row.get("first_result") or row.get("verification")
        subjects.append(QualificationSubject(
            subject_id=f"q01-sim009-{scenario_id}", record_kind="operation_run", claim_scope="run_local",
            predecessor_binding={"task_id": binding.task_id, "accepted_commit": binding.accepted_commit, "evidence_path": binding.evidence_path, "evidence_sha256": binding.evidence_sha256},
            qualification_run_id=str(measured.get("qualification_run_id") or f"q01-sim009-{scenario_id}"), scenario_id=scenario_id, backend_id=str(row["backend"]),
            component_version=str(result.get("component_version")) if isinstance(result, Mapping) else "sim009-scenario-v1",
            configuration_provenance={"run_local_configuration": config}, world_model_provenance={"world_model": world},
            timing={"simulation_time": measured["simulation_time"], "bounded_execution": measured.get("bounded_execution") is True},
            semantic_outcome={"accepted_outcome_kind": row.get("outcome_kind"), "accepted_decision": row.get("decision")},
        ))
    for subject in subjects:
        validate_subject(subject)
    return subjects


def collect_sim009_execution_result(template: QualificationSubject, result: Mapping[str, Any]) -> QualificationSubject:
    """Convert one explicit SIM-009 execution measurement without scenario reuse."""
    if template.predecessor_binding.get("task_id") != "TASK-SIM-009":
        raise ValueError("PREDECESSOR_TASK_MISMATCH")
    if result.get("qualification_run_id") != f"q01-sim009-{template.scenario_id}":
        raise ValueError("INVALID_QUALIFICATION_RUN_ID")
    if result.get("scenario_id") != template.scenario_id or result.get("backend_id") != template.backend_id:
        raise ValueError("CROSS_SCENARIO_ASSOCIATION")
    provenance = result.get("run_local_provenance")
    correlation = result.get("correlation_identity")
    outcome = result.get("semantic_outcome")
    if not all(isinstance(value, Mapping) for value in (provenance, correlation, outcome)) or not provenance:
        raise ValueError("MISSING_RUN_LOCAL_PROVENANCE")
    if not all(isinstance(correlation.get(field), str) and correlation[field] for field in ("mission_id", "request_id", "trace_id")):
        raise ValueError("MISSING_RUN_LOCAL_CORRELATION")
    timing = provenance.get("simulation_time")
    if not isinstance(timing, Mapping) or timing.get("source") not in {"gz_stats", "mujoco_steps_times_timestep", "mujoco_no_physics_start"} or not isinstance(timing.get("seconds"), (int, float)):
        raise ValueError("MISSING_STRUCTURED_SIMULATION_TIME")
    config, world = provenance.get("configuration_sha256"), provenance.get("world_model_sha256")
    if not all(isinstance(value, str) and len(value) == 64 for value in (config, world)):
        raise ValueError("MISSING_RUN_LOCAL_PROVENANCE")
    paths = provenance.get("source_paths")
    if not isinstance(paths, Mapping) or not all(isinstance(paths.get(field), str) and paths[field] for field in ("configuration", "world_model")):
        raise ValueError("MISSING_EXECUTION_ASSET_BINDING")
    if not isinstance(result.get("component_version"), str) or not isinstance(result.get("cleanup_complete"), bool):
        raise ValueError("INVALID_EXECUTION_RESULT")
    subject = QualificationSubject(**{**template.__dict__,
        "component_version": result["component_version"],
        "configuration_provenance": {"run_local_configuration": config},
        "world_model_provenance": {"world_model": world},
        "timing": {"simulation_time": timing["seconds"], "simulation_time_source": timing["source"], "cleanup_complete": result["cleanup_complete"], "bounded_execution": True},
        "semantic_outcome": dict(outcome),
        "correlation_identity": dict(correlation),
        "authority_paths": {"run_local_configuration": paths["configuration"], "world_model": paths["world_model"]},
    })
    validate_subject(subject)
    return subject


def aggregate_qualification_evidence(
    subjects: list[QualificationSubject], source_git_sha: str, *, required_subject_ids: set[str] | None = None,
) -> dict[str, Any]:
    """Produce fail-closed Q01 Evidence from already-qualified additive subjects."""
    if not isinstance(source_git_sha, str) or len(source_git_sha) != 40:
        raise ValueError("INVALID_SOURCE_GIT_SHA")
    if not subjects:
        raise ValueError("MISSING_QUALIFICATION_SUBJECT")
    identities = [subject.subject_id for subject in subjects]
    if len(set(identities)) != len(identities):
        raise ValueError("DUPLICATE_QUALIFICATION_SUBJECT")
    for subject in subjects:
        validate_subject(subject)
    missing = sorted((required_subject_ids or set()) - set(identities))
    result = "SIM_PROVENANCE_QUALIFICATION_READY" if not missing else "SIM_PROVENANCE_QUALIFICATION_BLOCKED"
    return {
        "schema_version": "1.0", "task_id": "TASK-SIM-Q01",
        "task_specific_result": result,
        "source_git_sha": source_git_sha, "simulation_only": True,
        "qualification_subjects": [asdict(subject) for subject in subjects],
        "validation": {"status": "PASS" if not missing else "BLOCKED", "subject_count": len(subjects), "missing_subject_ids": missing},
    }


def render_qualification_report(evidence: Mapping[str, Any]) -> str:
    """Render a non-authoritative report from canonical Evidence only."""
    validation = evidence.get("validation") if isinstance(evidence.get("validation"), Mapping) else {}
    lines = [
        "# SIM-Q01 Provenance Qualification",
        "",
        f"- Source revision: `{evidence.get('source_git_sha')}`",
        f"- Result: `{evidence.get('task_specific_result')}`",
        f"- Subject count: {validation.get('subject_count')}",
        f"- Validation: `{validation.get('status')}`",
    ]
    missing = validation.get("missing_subject_ids")
    if missing:
        lines.extend(["", "## Missing required subjects", *[f"- `{item}`" for item in missing]])
    return "\n".join(lines) + "\n"


def write_qualification_artifacts(evidence: Mapping[str, Any], evidence_path: Path, report_path: Path) -> tuple[Path, Path]:
    """Write canonical JSON and its derived Markdown companion atomically enough for task use."""
    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    evidence_path.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report_path.write_text(render_qualification_report(evidence), encoding="utf-8")
    return evidence_path, report_path


def _require(value: Any, reason: str) -> None:
    if value in _FAKE:
        raise ValueError("FAKE_NOT_APPLICABLE")
    if value is None:
        raise ValueError(reason)


def _hashes(values: Mapping[str, str], reason: str) -> None:
    if not values:
        raise ValueError(reason)
    for value in values.values():
        if not isinstance(value, str) or len(value) != 64 or value in _FAKE:
            raise ValueError(reason)


def validate_subject(subject: QualificationSubject) -> None:
    """Validate only explicit, applicable qualification facts."""
    _require(subject.subject_id, "MISSING_SUBJECT_ID")
    if subject.record_kind not in RECORD_KINDS:
        raise ValueError("INVALID_RECORD_KIND")
    if subject.claim_scope not in {"run_local", "profile", "version"}:
        raise ValueError("INVALID_CLAIM_SCOPE")
    binding = subject.predecessor_binding
    for field in ("task_id", "accepted_commit", "evidence_path", "evidence_sha256"):
        _require(binding.get(field), f"MISSING_PREDECESSOR_{field.upper()}")
    if len(str(binding["accepted_commit"])) != 40 or len(str(binding["evidence_sha256"])) != 64:
        raise ValueError("INVALID_PREDECESSOR_BINDING")
    _require(subject.backend_id, "MISSING_BACKEND")
    _require(subject.component_version, "MISSING_COMPONENT_VERSION")
    _hashes(subject.configuration_provenance, "MISSING_CONFIGURATION_PROVENANCE")
    _hashes(subject.world_model_provenance, "MISSING_WORLD_MODEL_PROVENANCE")
    if len(set(subject.configuration_provenance.values())) != len(subject.configuration_provenance):
        raise ValueError("SEMANTIC_HASH_ALIAS")
    if subject.record_kind == "operation_run":
        _require(subject.qualification_run_id, "MISSING_QUALIFICATION_RUN_ID")
        _require(subject.scenario_id, "MISSING_SCENARIO_ID")
        if not isinstance(subject.timing, Mapping) or not isinstance(subject.timing.get("simulation_time"), (int, float)):
            raise ValueError("MISSING_STRUCTURED_SIMULATION_TIME")
        if not isinstance(subject.semantic_outcome, Mapping):
            raise ValueError("MISSING_SEMANTIC_OUTCOME")
    elif subject.record_kind == "profile_aggregate":
        _require(subject.profile_id, "MISSING_PROFILE_ID")
        if subject.qualification_run_id is not None or subject.scenario_id is not None:
            raise ValueError("AGGREGATE_OPERATION_IMPERSONATION")
    else:
        if subject.claim_scope != "version" or subject.qualification_run_id is not None:
            raise ValueError("INVALID_VERSION_QUALIFICATION")
