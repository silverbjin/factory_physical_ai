"""Fail-closed accepted simulation evidence indexing and regression checks."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
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
RUN_EXTRACTOR_TASKS = frozenset({"SIM-004", "SIM-005", "SIM-007", "SIM-008", "SIM-009"})
IDENTITY_FIELDS = ("mission_id", "request_id", "action_id", "trace_id")
CORRELATION_FIELDS = (*IDENTITY_FIELDS, "skill_result", "verification_result", "failure_code", "recovery_decision")

Q01_BINDING = {
    "acceptance_recording_commit": "a1f1539c27f61fb2ce52aed33ceaf1bfe343912c",
    "acceptance_path": "results/reviews/SIM-Q01-MIN_acceptance.json",
    "acceptance_task_id": "TASK-SIM-Q01-MIN",
    "accepted_commit": "b55bc4fc2435e83c3761457b92d9e14892e39435",
    "evidence_path": "results/simulation/SIM-Q01_provenance_qualification.json",
    "evidence_sha256": "dbd2fc20f6072f8889466fff29b80ec874d105b37c5633e909c633facdb2eb6a",
    "evidence_task_id": "TASK-SIM-Q01",
    "result": "SIM_PROVENANCE_QUALIFICATION_READY",
}
Q01_SUBJECTS = {
    "q01-sim008-normal-system-authority": ("SIM-008", "SIM_NORMAL_BRAKE_ECU_LINE_B", "gazebo", "sim008-normal-system-e2e-v1"),
    "q01-sim009-SIM009-NAV-BLOCKED": ("SIM-009", "SIM009-NAV-BLOCKED", "gazebo", "sim004-navigation-backend-v2"),
    "q01-sim009-SIM009-NAV-ABORTED": ("SIM-009", "SIM009-NAV-ABORTED", "gazebo", "sim004-navigation-backend-v2"),
    "q01-sim009-SIM009-NAV-TIMEOUT-RETRY": ("SIM-009", "SIM009-NAV-TIMEOUT-RETRY", "gazebo", "sim004-navigation-backend-v2"),
    "q01-sim009-SIM009-NAV-TF-UNAVAILABLE": ("SIM-009", "SIM009-NAV-TF-UNAVAILABLE", "gazebo", "sim004-navigation-backend-v2"),
    "q01-sim009-SIM009-VLA-GRASP-MISS": ("SIM-009", "SIM009-VLA-GRASP-MISS", "mujoco", "sim005-mujoco-vla-backend-v1"),
    "q01-sim009-SIM009-VLA-CONTACT-LOSS": ("SIM-009", "SIM009-VLA-CONTACT-LOSS", "mujoco", "sim005-mujoco-vla-backend-v1"),
    "q01-sim009-SIM009-VLA-WORKSPACE-LIMIT": ("SIM-009", "SIM009-VLA-WORKSPACE-LIMIT", "mujoco", "sim005-mujoco-vla-backend-v1"),
    "q01-sim009-SIM009-VLA-TIMEOUT": ("SIM-009", "SIM009-VLA-TIMEOUT", "mujoco", "sim005-mujoco-vla-backend-v1"),
    "q01-sim009-SIM009-VLA-AMBIGUOUS": ("SIM-009", "SIM009-VLA-AMBIGUOUS", "mujoco", "sim005-mujoco-vla-backend-v1"),
    "q01-sim009-SIM009-VLA-UNKNOWN": ("SIM-009", "SIM009-VLA-UNKNOWN", "mujoco", "sim005-mujoco-vla-backend-v1"),
}
Q01_PREDECESSOR_ACCEPTANCES = {
    "SIM-004": "ebf84580f141f9d8ea0962d008ef35a5d14b7dd6",
    "SIM-005": "ebf84580f141f9d8ea0962d008ef35a5d14b7dd6",
    "SIM-007": "8ecca674f2e5c39df175362f98d43f174e44923b",
    "SIM-008": "162ffaa4e78b255630cd1204aa43fa2d7c229108",
    "SIM-009": "2e85d275277b3c2bbc331b04f8b6c3a9c81fe8a3",
}
Q01_SUPPORT_CLAIMS = {
    "TASK-SIM-004": {"component_version", "runtime_identity", "world_authority", "bridge_authority", "runner_authority"},
    "TASK-SIM-005": {"mujoco_version", "model_scene_authority", "configuration_source_authority", "version_wide_seed_timestep_authority", "accepted_initial_state_authority"},
    "TASK-SIM-007": {"profile_identity", "profile_source_configuration_authority", "accepted_aggregate_outcome"},
}

HISTORICAL_DIAGNOSTIC_FAILURES = {
    ("SIM-004", "success"): frozenset({"MISSING_SIMULATION_TIME"}),
    ("SIM-004", "blocked"): frozenset({"MISSING_SIMULATION_TIME"}),
    ("SIM-004", "timeout_reconciliation"): frozenset({"MISSING_SIMULATION_TIME"}),
    **{("SIM-005", scenario): frozenset({"MISSING_TRACE_ID", "INCOMPLETE_CORRELATION_IDENTITY"}) for scenario in (
        "mujoco-place-nominal", "mujoco-grasp-miss", "mujoco-contact-loss",
        "mujoco-workspace-limit", "mujoco-invalid-observation", "mujoco-timeout", "mujoco-unknown",
    )},
    **{("SIM-007", scenario): frozenset({"MISSING_SOURCE_CONFIG_HASHES"}) for scenario in (
        "deterministic", "navigation_physics", "manipulation_physics", "system",
    )},
}
QUALIFIED_RUN_FAILURES = {
    ("SIM-008", "SIM_NORMAL_BRAKE_ECU_LINE_B"): (
        "q01-sim008-normal-system-authority",
        frozenset({"MISSING_BRIDGE_SHA256", "MISSING_LAUNCH_SHA256"}),
    ),
    **{("SIM-009", scenario): (subject_id, frozenset({
        "MISSING_SOURCE_HASH:run_config_sha256", "MISSING_WORLD_MODEL_SHA256", "MISSING_SIMULATION_TIME",
    })) for subject_id, scenario in (
        ("q01-sim009-SIM009-NAV-BLOCKED", "SIM009-NAV-BLOCKED"),
        ("q01-sim009-SIM009-NAV-ABORTED", "SIM009-NAV-ABORTED"),
        ("q01-sim009-SIM009-NAV-TIMEOUT-RETRY", "SIM009-NAV-TIMEOUT-RETRY"),
        ("q01-sim009-SIM009-NAV-TF-UNAVAILABLE", "SIM009-NAV-TF-UNAVAILABLE"),
        ("q01-sim009-SIM009-VLA-GRASP-MISS", "SIM009-VLA-GRASP-MISS"),
        ("q01-sim009-SIM009-VLA-CONTACT-LOSS", "SIM009-VLA-CONTACT-LOSS"),
        ("q01-sim009-SIM009-VLA-WORKSPACE-LIMIT", "SIM009-VLA-WORKSPACE-LIMIT"),
        ("q01-sim009-SIM009-VLA-TIMEOUT", "SIM009-VLA-TIMEOUT"),
        ("q01-sim009-SIM009-VLA-AMBIGUOUS", "SIM009-VLA-AMBIGUOUS"),
        ("q01-sim009-SIM009-VLA-UNKNOWN", "SIM009-VLA-UNKNOWN"),
    )},
}
REQUIRED_RUN_FAILURE_CLASSES = (
    "HISTORICAL_DIAGNOSTIC_ONLY_NON_GATING",
    "EXPLICITLY_QUALIFIED_BY_Q01",
    "STILL_BLOCKING",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def failure_signatures(pytest_output: str) -> dict[str, str]:
    """Extract non-empty stable signatures from pytest summary and trace blocks."""
    summary: list[tuple[str, str]] = []
    trace_blocks: list[str] = []
    current_block: list[str] | None = None
    header = re.compile(r"^_+(?: ERROR collecting)? .+ _+$")
    signatures: dict[str, str] = {}
    for line in pytest_output.splitlines():
        if header.match(line):
            if current_block is not None:
                trace_blocks.append("\n".join(current_block))
            current_block = []
            continue
        if current_block is not None:
            if line.startswith("E   ") or line.startswith("E "):
                current_block.append(line[2:].strip())
        match = re.match(r"^(?:FAILED|ERROR) (.+?)(?: - (.*))?$", line)
        if match:
            node, detail = match.groups()
            summary.append((node, detail or ""))
    if current_block is not None:
        trace_blocks.append("\n".join(current_block))

    for index, (node, detail) in enumerate(summary):
        source = detail or (trace_blocks[index] if index < len(trace_blocks) else "")
        normalized = re.sub(r"0x[0-9a-fA-F]+|\b\d+(?:\.\d+)?\b", "<n>", source)
        normalized = re.sub(r"/tmp/[^\s:'\"]+", "<tmp>", normalized)
        normalized = re.sub(r"\s+", " ", normalized).strip()
        signatures[node] = hashlib.sha256(normalized.encode("utf-8")).hexdigest() if normalized else ""
    return signatures


def classify_regression_failures(current: Mapping[str, str], baseline: Mapping[str, str]) -> str:
    """Classify failures only after an identical-command baseline comparison."""
    if not current:
        return "PASS"
    if any(not signature for signature in (*current.values(), *baseline.values())):
        return "POSSIBLY_TASK_RELATED"
    return "PROVEN_PREEXISTING" if dict(current) == dict(baseline) else "POSSIBLY_TASK_RELATED"


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


def _q01_fail(reason: str) -> None:
    raise ValueError(f"Q01_{reason}")


def _q01_profile(value: Any) -> str | None:
    return {"gazebo": "gazebo", "gazebo_navigation": "gazebo", "mujoco": "mujoco"}.get(value)


def _resolve_q01_predecessor(root: Path, short_id: str) -> dict[str, Any]:
    """Resolve a Q01 predecessor through its pinned Acceptance tree object."""
    acceptance_commit = Q01_PREDECESSOR_ACCEPTANCES[short_id]
    acceptance_path = f"results/reviews/{short_id}_acceptance.json"
    _git(root, "cat-file", "-e", f"{acceptance_commit}^{{commit}}")
    try:
        acceptance = json.loads(_git(root, "show", f"{acceptance_commit}:{acceptance_path}"))
    except json.JSONDecodeError as exc:
        _q01_fail("MALFORMED_PREDECESSOR_ACCEPTANCE")
        raise exc  # pragma: no cover
    if (not isinstance(acceptance, Mapping) or acceptance.get("task_id") != f"TASK-{short_id}"
            or acceptance.get("status") != "ACCEPT"):
        _q01_fail("INVALID_PREDECESSOR_ACCEPTANCE")
    try:
        return resolve_accepted_evidence(root, short_id, acceptance)
    except (OSError, ValueError, json.JSONDecodeError):
        _q01_fail("UNRESOLVABLE_PREDECESSOR")
    raise AssertionError("unreachable")  # pragma: no cover


def _validate_q01_applicability(subject: Mapping[str, Any]) -> None:
    applicability = subject.get("applicability")
    timing = subject.get("timing")
    if not isinstance(applicability, Mapping) or not isinstance(timing, Mapping):
        _q01_fail("INVALID_APPLICABILITY")
    for field in ("physics_measurement", "structured_simulator_time"):
        claim = applicability.get(field)
        if not isinstance(claim, Mapping):
            _q01_fail("INVALID_APPLICABILITY")
        state = claim.get("state")
        if state == "REQUIRED":
            observation = timing.get("physics_measurement") if field == "physics_measurement" else timing.get("simulation_time")
            source = observation.get("source") if isinstance(observation, Mapping) else timing.get("simulation_time_source")
            if ((isinstance(observation, Mapping) and isinstance(observation.get("seconds"), (int, float))) or isinstance(observation, (int, float))) and isinstance(source, str) and source:
                continue
            _q01_fail("MISSING_REQUIRED_OBSERVATION")
        if state == "NOT_APPLICABLE":
            if not isinstance(claim.get("justification"), str) or not claim["justification"]:
                _q01_fail("MISSING_NOT_APPLICABLE_JUSTIFICATION")
            execution = claim.get("execution_state")
            if not isinstance(execution, Mapping):
                execution = timing.get("execution_state")
            if not isinstance(execution, Mapping) or execution.get("simulator_started") is not False or execution.get("physics_started") is not False:
                _q01_fail("INVALID_NOT_APPLICABLE")
            continue
        _q01_fail("INVALID_APPLICABILITY")


def validate_q01_chain(root: Path, acceptance: Mapping[str, Any], evidence: Mapping[str, Any]) -> None:
    """Validate Q01 content without treating either authority as mutable state."""
    if (acceptance.get("task_id") != Q01_BINDING["acceptance_task_id"]
            or acceptance.get("status") != "ACCEPT"
            or acceptance.get("workflow_complete") is not True
            or acceptance.get("accepted_commit") != Q01_BINDING["accepted_commit"]):
        _q01_fail("INVALID_ACCEPTANCE")
    if (evidence.get("task_id") != Q01_BINDING["evidence_task_id"]
            or evidence.get("task_specific_result") != Q01_BINDING["result"]
            or evidence.get("simulation_only") is not True):
        _q01_fail("INVALID_EVIDENCE")
    validation = evidence.get("validation")
    subjects = evidence.get("qualification_subjects")
    if (not isinstance(validation, Mapping) or validation.get("status") != "PASS"
            or not isinstance(subjects, list)):
        _q01_fail("INVALID_SUBJECTS")
    ids = [item.get("subject_id") for item in subjects if isinstance(item, Mapping)]
    if len(subjects) != len(Q01_SUBJECTS) or len(ids) != len(set(ids)) or set(ids) != set(Q01_SUBJECTS):
        _q01_fail("SUBJECT_SET_MISMATCH")
    runs: set[tuple[Any, Any]] = set()
    mappings: set[tuple[Any, Any]] = set()
    scenario_executions: set[tuple[Any, Any]] = set()
    for subject in subjects:
        if not isinstance(subject, Mapping):
            _q01_fail("INVALID_SUBJECT")
        subject_id = subject.get("subject_id")
        expected = Q01_SUBJECTS.get(subject_id)
        if expected is None or subject.get("claim_scope") != "run_local" or subject.get("record_kind") != "operation_run":
            _q01_fail("INVALID_SUBJECT_SCOPE")
        predecessor_task, scenario_id, profile, component = expected
        if (subject.get("scenario_id") != scenario_id or _q01_profile(subject.get("backend_id")) != profile
                or subject.get("component_version") != component):
            _q01_fail("SUBJECT_MAPPING_MISMATCH")
        identity = subject.get("correlation_identity")
        required_identity = ("mission_id", "request_id", "trace_id") if predecessor_task == "SIM-008" else IDENTITY_FIELDS
        if not isinstance(identity, Mapping) or any(not isinstance(identity.get(key), str) or not identity[key] for key in required_identity):
            _q01_fail("INVALID_CORRELATION_IDENTITY")
        binding = subject.get("predecessor_binding")
        if not isinstance(binding, Mapping) or binding.get("task_id") != f"TASK-{predecessor_task}":
            _q01_fail("INVALID_PREDECESSOR_BINDING")
        resolved = _resolve_q01_predecessor(root, predecessor_task)
        if any(resolved[key] != binding.get(key) for key in ("accepted_commit", "evidence_path", "evidence_sha256")):
            _q01_fail("PREDECESSOR_BINDING_MISMATCH")
        run_key = (subject.get("qualification_run_id"), subject.get("scenario_id"))
        mapping_key = (binding.get("task_id"), subject.get("scenario_id"))
        if not all(isinstance(value, str) and value for value in run_key) or run_key in runs or mapping_key in mappings:
            _q01_fail("DUPLICATE_AUTHORITY")
        runs.add(run_key); mappings.add(mapping_key)
        semantic = subject.get("semantic_outcome")
        execution_identity = semantic.get("execution_identity") if isinstance(semantic, Mapping) else None
        if predecessor_task == "SIM-009":
            scenario_execution_id = execution_identity.get("scenario_execution_id") if isinstance(execution_identity, Mapping) else None
            if not isinstance(scenario_execution_id, str) or not scenario_execution_id:
                _q01_fail("INVALID_SCENARIO_EXECUTION_IDENTITY")
            execution_key = (subject.get("qualification_run_id"), scenario_execution_id)
            if execution_key in scenario_executions:
                _q01_fail("DUPLICATE_AUTHORITY")
            scenario_executions.add(execution_key)
        _validate_q01_applicability(subject)
    immutable = evidence.get("immutable_authority_bindings")
    if not isinstance(immutable, Mapping):
        _q01_fail("INVALID_SUPPORT_AUTHORITY")
    for task_id, allowed_claims in Q01_SUPPORT_CLAIMS.items():
        item = immutable.get(task_id)
        if (not isinstance(item, Mapping) or item.get("claim_scope") != "immutable_accepted_authority"
                or not isinstance(item.get("claims"), list) or set(item["claims"]) != allowed_claims):
            _q01_fail("INVALID_SUPPORT_AUTHORITY")
        binding = item.get("predecessor_binding")
        short_id = task_id[5:]
        if not isinstance(binding, Mapping):
            _q01_fail("INVALID_SUPPORT_AUTHORITY")
        resolved = _resolve_q01_predecessor(root, short_id)
        if any(resolved[key] != binding.get(key) for key in ("accepted_commit", "evidence_path", "evidence_sha256")):
            _q01_fail("SUPPORT_PREDECESSOR_BINDING_MISMATCH")


def resolve_q01_qualification(root: Path) -> dict[str, Any]:
    """Resolve Q01 only from its pinned Git objects, never a worktree path."""
    _git(root, "cat-file", "-e", f"{Q01_BINDING['acceptance_recording_commit']}^{{commit}}")
    raw_acceptance = _git(root, "show", f"{Q01_BINDING['acceptance_recording_commit']}:{Q01_BINDING['acceptance_path']}")
    try:
        acceptance = json.loads(raw_acceptance)
    except json.JSONDecodeError as exc:
        _q01_fail("MALFORMED_ACCEPTANCE")
        raise exc  # pragma: no cover
    _git(root, "cat-file", "-e", f"{Q01_BINDING['accepted_commit']}^{{commit}}")
    raw_evidence = _git(root, "show", f"{Q01_BINDING['accepted_commit']}:{Q01_BINDING['evidence_path']}")
    if hashlib.sha256(raw_evidence).hexdigest() != Q01_BINDING["evidence_sha256"]:
        _q01_fail("EVIDENCE_HASH_MISMATCH")
    try:
        evidence = json.loads(raw_evidence)
    except json.JSONDecodeError as exc:
        _q01_fail("MALFORMED_EVIDENCE")
        raise exc  # pragma: no cover
    if not isinstance(acceptance, Mapping) or not isinstance(evidence, Mapping):
        _q01_fail("MALFORMED_CHAIN")
    validate_q01_chain(root, acceptance, evidence)
    normalized: list[dict[str, Any]] = []
    for subject in evidence["qualification_subjects"]:
        binding = subject["predecessor_binding"]
        short_id = str(binding["task_id"])[5:]
        predecessor = _resolve_q01_predecessor(root, short_id)
        if any(predecessor[key] != binding.get(key) for key in ("accepted_commit", "evidence_path", "evidence_sha256")):
            _q01_fail("PREDECESSOR_BINDING_MISMATCH")
        expected = Q01_SUBJECTS[subject["subject_id"]]
        candidates = [run for run in extract_bound_runs(short_id, predecessor["evidence"]) if run["scenario_id"] == expected[1]]
        if len(candidates) != 1:
            _q01_fail("AMBIGUOUS_PREDECESSOR_SCENARIO")
        observation = dict(subject)
        observation.update({
            "authority_kind": "qualification_observation", "qualification_task_id": Q01_BINDING["acceptance_task_id"],
            "qualification_evidence_task_id": Q01_BINDING["evidence_task_id"],
            "qualification_accepted_commit": Q01_BINDING["accepted_commit"],
            "qualification_evidence_sha256": Q01_BINDING["evidence_sha256"], "replay_applicable": False,
            "backend_profile": expected[2], "physics_semantic_applicable": subject["applicability"]["physics_measurement"]["state"] == "REQUIRED",
        })
        normalized.append({
            "subject_id": subject["subject_id"],
            "historical_oracle": {"task_id": binding["task_id"], "accepted_commit": predecessor["accepted_commit"], "evidence_path": predecessor["evidence_path"], "evidence_sha256": predecessor["evidence_sha256"], "scenario_source_path": candidates[0]["source_json_path"], "envelope": candidates[0]["envelope"]},
            "qualification_observation": observation,
            "replay_applicable": False,
        })
    return {"acceptance_task_id": Q01_BINDING["acceptance_task_id"], "evidence_task_id": Q01_BINDING["evidence_task_id"], "evidence_sha256": Q01_BINDING["evidence_sha256"], "qualification_subjects": normalized}


def _valid_qualified_subjects(q01: Mapping[str, Any] | None) -> dict[tuple[str, str], str]:
    """Return only exact, separately-namespaced Q01 subject mappings."""
    if not isinstance(q01, Mapping):
        return {}
    linked_subjects = q01.get("qualification_subjects")
    if not isinstance(linked_subjects, list):
        return {}
    mappings: dict[tuple[str, str], str] = {}
    for linked in linked_subjects:
        if not isinstance(linked, Mapping):
            continue
        subject_id = linked.get("subject_id")
        expected = Q01_SUBJECTS.get(subject_id)
        historical = linked.get("historical_oracle")
        observation = linked.get("qualification_observation")
        if not isinstance(expected, tuple) or not isinstance(historical, Mapping) or not isinstance(observation, Mapping):
            continue
        predecessor_task, scenario_id, _, _ = expected
        envelope = historical.get("envelope")
        if (
            historical.get("task_id") != f"TASK-{predecessor_task}"
            or not isinstance(envelope, Mapping)
            or envelope.get("scenario_id") != scenario_id
            or observation.get("subject_id") != subject_id
            or observation.get("scenario_id") != scenario_id
            or observation.get("claim_scope") != "run_local"
        ):
            continue
        mappings[(predecessor_task, scenario_id)] = subject_id
    return mappings


def classify_required_run_failures(
    index: list[Mapping[str, Any]], q01: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Classify each retained historical failure without backfilling its source row."""
    qualified_subjects = _valid_qualified_subjects(q01)
    entries: list[dict[str, Any]] = []
    failure_pattern = re.compile(r"^RUN\[(?P<index>\d+)\]:(?P<failure>.+)$")
    for row in index:
        short_id = row.get("short_task_id")
        if not isinstance(short_id, str) or short_id not in RUN_EXTRACTOR_TASKS:
            continue
        sources = row.get("run_sources")
        validation = row.get("run_validation")
        failures = validation.get("failures") if isinstance(validation, Mapping) else []
        if not isinstance(sources, list) or not isinstance(failures, list):
            continue
        for raw_failure in failures:
            if not isinstance(raw_failure, str):
                continue
            match = failure_pattern.match(raw_failure)
            position = int(match.group("index")) if match else None
            failure = match.group("failure") if match else raw_failure
            source = sources[position] if position is not None and position < len(sources) and isinstance(sources[position], Mapping) else {}
            scenario_id = source.get("scenario_id") if isinstance(source.get("scenario_id"), str) else None
            historical_allowed = HISTORICAL_DIAGNOSTIC_FAILURES.get((short_id, scenario_id))
            qualified = QUALIFIED_RUN_FAILURES.get((short_id, scenario_id))
            subject_id = qualified_subjects.get((short_id, scenario_id))
            if historical_allowed is not None and failure in historical_allowed:
                classification = "HISTORICAL_DIAGNOSTIC_ONLY_NON_GATING"
            elif qualified is not None and subject_id == qualified[0] and failure in qualified[1]:
                classification = "EXPLICITLY_QUALIFIED_BY_Q01"
            else:
                classification = "STILL_BLOCKING"
            entries.append({
                "source_task": short_id,
                "run_index": position,
                "scenario_id": scenario_id,
                "failure": failure,
                "classification": classification,
                "qualification_subject_id": subject_id,
            })
    counts = {kind: sum(entry["classification"] == kind for entry in entries) for kind in REQUIRED_RUN_FAILURE_CLASSES}
    return {"entries": entries, "counts": counts, "status": "PASS" if counts["STILL_BLOCKING"] == 0 else "BLOCKED"}


def _identity(raw: Mapping[str, Any]) -> dict[str, Any]:
    return {field: raw.get(field) for field in IDENTITY_FIELDS}


def _record(source_json_path: str, scenario_id: str, identity_source: Mapping[str, Any], envelope: Mapping[str, Any]) -> dict[str, Any]:
    """Create a trace row only from one explicit source subtree."""
    return {
        "source_json_path": source_json_path,
        "scenario_id": scenario_id,
        "identity": _identity(identity_source),
        "envelope": dict(envelope),
    }


def _scenario_result(scenario: Mapping[str, Any]) -> Mapping[str, Any] | None:
    for key in ("result", "timeout", "first_result", "retry_result", "verification", "reconciliation"):
        value = scenario.get(key)
        if isinstance(value, Mapping):
            return value
    return None


def _declared_scenario_ids(short_id: str, raw: Mapping[str, Any]) -> list[str]:
    if short_id == "SIM-008":
        scenario = raw.get("scenario")
        if isinstance(scenario, Mapping) and isinstance(scenario.get("scenario_id"), str):
            return [scenario["scenario_id"]]
    scenarios = raw.get("scenarios")
    if not isinstance(scenarios, list):
        return []
    values: list[str] = []
    for scenario in scenarios:
        if not isinstance(scenario, Mapping):
            continue
        value = scenario.get("id") or scenario.get("scenario") or scenario.get("scenario_id")
        if isinstance(value, str) and value:
            values.append(value)
    return values


def _asset_hashes(raw: Mapping[str, Any]) -> dict[str, str]:
    """Return only explicitly declared artifact hashes, never an Evidence digest."""
    hashes = raw.get("source_hashes")
    if isinstance(hashes, Mapping) and all(_valid_hash(value) for value in hashes.values()):
        return {str(key): value for key, value in hashes.items()}
    provenance = raw.get("provenance")
    assets = provenance.get("assets") if isinstance(provenance, Mapping) else None
    if isinstance(assets, list):
        return {
            str(asset["path"]): asset["sha256"]
            for asset in assets
            if isinstance(asset, Mapping) and isinstance(asset.get("path"), str) and _valid_hash(asset.get("sha256"))
        }
    return {}


def _asset(raw: Mapping[str, Any], expected_path: str) -> tuple[str | None, str | None]:
    """Resolve one explicitly named asset and its JSON-pointer authority."""
    provenance = raw.get("provenance")
    assets = provenance.get("assets") if isinstance(provenance, Mapping) else None
    if not isinstance(assets, list):
        return None, None
    matches = [
        (asset.get("sha256"), f"/provenance/assets/{index}/sha256")
        for index, asset in enumerate(assets)
        if isinstance(asset, Mapping) and asset.get("path") == expected_path and _valid_hash(asset.get("sha256"))
    ]
    return matches[0] if len(matches) == 1 else (None, None)


def _sim004_execution(raw: Mapping[str, Any], action_id: Any) -> tuple[Mapping[str, Any] | None, int | None]:
    lifecycle = raw.get("bounded_lifecycle")
    executions = lifecycle.get("executions") if isinstance(lifecycle, Mapping) else None
    if not isinstance(action_id, str) or not isinstance(executions, list):
        return None, None
    matches = [
        (execution, index)
        for index, execution in enumerate(executions)
        if isinstance(execution, Mapping) and execution.get("action_id") == action_id
    ]
    return matches[0] if len(matches) == 1 else (None, None)


def _profile_for(short_id: str, scenario: Mapping[str, Any]) -> str | None:
    """Map only documented task/profile labels to the normalized profile."""
    if short_id == "SIM-007":
        return {
            "deterministic": "deterministic",
            "navigation_physics": "gazebo",
            "manipulation_physics": "mujoco",
            "system": "gazebo",
        }.get(scenario.get("profile"))
    if short_id == "SIM-009":
        return {
            "gazebo_navigation": "gazebo", "mujoco": "mujoco", "verification": "verification",
            "navigation": "gazebo", "contract": "deterministic",
        }.get(scenario.get("backend"))
    return BACKEND_PROFILES.get(short_id)


def _artifact_context(short_id: str, raw: Mapping[str, Any], scenario: Mapping[str, Any]) -> dict[str, Any]:
    """Explicit artifact-level context with provenance paths for a normalized row."""
    provenance = raw.get("provenance") if isinstance(raw.get("provenance"), Mapping) else {}
    profile = _profile_for(short_id, scenario)
    context: dict[str, Any] = {
        "backend_profile": profile,
        "source_hashes": _asset_hashes(raw),
        "artifact_context_paths": ["/provenance", "/source_hashes"],
    }
    if isinstance(provenance, Mapping) and provenance.get("physical_target") is False:
        context["simulation_only"] = True
    if short_id == "SIM-008":
        system = raw.get("system_profile") if isinstance(raw.get("system_profile"), Mapping) else {}
        specification = raw.get("scenario") if isinstance(raw.get("scenario"), Mapping) else {}
        context.update({
            "simulation_only": True,
            "source_hashes": {key: value for key, value in {
                "scenario_config": specification.get("config_sha256"), "scenario": specification.get("scenario_sha256"),
                "world": specification.get("world_sha256"),
            }.items() if _valid_hash(value)},
            "simulator_provenance": {
                "ros2_identity": system.get("integrated_world"),
                "gazebo_version": system.get("integrated_world"),
                "world_model_sha256": specification.get("world_sha256"),
            },
            "artifact_context_paths": ["/system_profile", "/scenario"],
        })
    elif short_id == "SIM-005" and isinstance(provenance, Mapping):
        config_hash, config_path = _asset(raw, "configs/simulation/sim005_mujoco_manipulation.yaml")
        scene_hash, scene_path = _asset(raw, "data/simulation/sim005_mujoco_manipulation.xml")
        backend_hash, backend_path = _asset(raw, "src/simulation_runtime/mujoco_vla_backend.py")
        declared_hashes = raw.get("source_hashes") if isinstance(raw.get("source_hashes"), Mapping) else {}
        runner_hash = declared_hashes.get("runner") if _valid_hash(declared_hashes.get("runner")) else None
        context.update({
            "simulation_only": provenance.get("physical_target") is False,
            "source_hashes": {key: value for key, value in {
                "backend_source_sha256": backend_hash,
                "runner_source_sha256": runner_hash,
                "model_config_sha256": config_hash,
                "model_scene_sha256": scene_hash,
            }.items() if _valid_hash(value)},
            "simulator_provenance": {
                "mujoco_version": provenance.get("mujoco_version"),
                "model_scene_config_sha256": (
                    {"config": config_hash, "scene": scene_hash}
                    if _valid_hash(config_hash) and _valid_hash(scene_hash) else None
                ),
                "seed_identity": provenance.get("seed"), "timestep": provenance.get("timestep_seconds"),
                "step_settings": {"maximum_steps": provenance.get("maximum_steps")},
                "initial_state_identity": provenance.get("initial_state_id"),
            },
            "provenance_authority": {
                "backend_source_sha256": backend_path,
                "runner_source_sha256": "/source_hashes/runner",
                "model_config_sha256": config_path,
                "model_scene_sha256": scene_path,
                "mujoco_version": "/provenance/mujoco_version",
                "seed_identity": "/provenance/seed",
                "timestep": "/provenance/timestep_seconds",
                "step_settings": "/provenance/maximum_steps",
                "initial_state_identity": "/provenance/initial_state_id",
            },
        })
    elif short_id == "SIM-004":
        runtime = raw.get("runtime_identity") if isinstance(raw.get("runtime_identity"), Mapping) else {}
        gazebo = runtime.get("gazebo") if isinstance(runtime.get("gazebo"), Mapping) else {}
        ros2 = runtime.get("ros2") if isinstance(runtime.get("ros2"), Mapping) else {}
        hashes = _asset_hashes(raw)
        context["simulator_provenance"] = {
            "ros2_identity": ros2.get("stdout"), "gazebo_version": gazebo.get("stdout"),
            "world_model_sha256": next((value for key, value in hashes.items() if key.endswith(".sdf")), None),
        }
    elif short_id == "SIM-009":
        authority = raw.get("simulation_authority") if isinstance(raw.get("simulation_authority"), Mapping) else {}
        context["simulation_only"] = authority.get("physical_dependency") is False
        manifest = raw.get("manifest_sha256")
        context["source_hashes"] = {"manifest_sha256": manifest} if _valid_hash(manifest) else {}
        context["provenance_authority"] = {"manifest_sha256": "/manifest_sha256"}
        context["artifact_context_paths"] = ["/simulation_authority", "/infrastructure"]
    return context


def _supporting_backend_qualification(
    raw: Mapping[str, Any],
    result: Mapping[str, Any],
    backend_profile: Any,
    supporting: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any] | None:
    """Bind version-wide backend facts through an exact accepted binding."""
    component_version = result.get("component_version")
    task_id = {
        "sim004-navigation-backend-v2": "SIM-004",
        "sim005-mujoco-vla-backend-v1": "SIM-005",
    }.get(component_version)
    if task_id is None:
        return None
    if (task_id, backend_profile) not in {("SIM-004", "gazebo"), ("SIM-005", "mujoco")}:
        return None
    bindings = raw.get("accepted_bindings")
    binding_wrapper = bindings.get(task_id) if isinstance(bindings, Mapping) else None
    binding = binding_wrapper.get("acceptance") if isinstance(binding_wrapper, Mapping) else None
    resolved = supporting.get(task_id)
    if not isinstance(binding, Mapping) or not isinstance(resolved, Mapping):
        return None
    evidence_binding = binding.get("evidence")
    if (
        binding.get("task_id") != f"TASK-{task_id}"
        or binding.get("status") != "ACCEPT"
        or binding.get("accepted_commit") != resolved.get("accepted_commit")
        or not isinstance(evidence_binding, Mapping)
        or evidence_binding.get("path") != resolved.get("evidence_path")
        or evidence_binding.get("sha256") != resolved.get("evidence_sha256")
    ):
        return None
    evidence = resolved.get("evidence")
    if not isinstance(evidence, Mapping):
        return None
    provenance = evidence.get("provenance") if isinstance(evidence.get("provenance"), Mapping) else {}
    if task_id == "SIM-005":
        if provenance.get("backend_id") != component_version:
            return None
        config_hash, _ = _asset(evidence, "configs/simulation/sim005_mujoco_manipulation.yaml")
        scene_hash, _ = _asset(evidence, "data/simulation/sim005_mujoco_manipulation.xml")
        return {
            "source_task": task_id,
            "component_version": component_version,
            "accepted_commit": resolved["accepted_commit"],
            "evidence_path": resolved["evidence_path"],
            "evidence_sha256": resolved["evidence_sha256"],
            "mujoco_version": provenance.get("mujoco_version"),
            "model_config_sha256": config_hash,
            "model_scene_sha256": scene_hash,
            "seed_identity": provenance.get("seed"),
            "timestep": provenance.get("timestep_seconds"),
            "step_settings": {"maximum_steps": provenance.get("maximum_steps")},
            "initial_state_identity": provenance.get("initial_state_id"),
        }
    scenarios = evidence.get("scenarios")
    versions = {
        child.get("component_version")
        for scenario in scenarios if isinstance(scenarios, list) and isinstance(scenario, Mapping)
        for key in ("result", "timeout", "first_result", "retry_result", "verification", "reconciliation")
        for child in [scenario.get(key)]
        if isinstance(child, Mapping) and isinstance(child.get("component_version"), str)
    } if isinstance(scenarios, list) else set()
    if versions != {component_version}:
        return None
    runtime = evidence.get("runtime_identity") if isinstance(evidence.get("runtime_identity"), Mapping) else {}
    ros2 = runtime.get("ros2") if isinstance(runtime.get("ros2"), Mapping) else {}
    gazebo = runtime.get("gazebo") if isinstance(runtime.get("gazebo"), Mapping) else {}
    world_hash, _ = _asset(evidence, "data/simulation/sim004_navigation_proxy_world.sdf")
    bridge_hash, _ = _asset(evidence, "configs/simulation/sim004_navigation_proxy.yaml")
    launch_hash, _ = _asset(evidence, "scripts/run_simulation_navigation.py")
    return {
        "source_task": task_id,
        "component_version": component_version,
        "accepted_commit": resolved["accepted_commit"],
        "evidence_path": resolved["evidence_path"],
        "evidence_sha256": resolved["evidence_sha256"],
        "ros2_identity": ros2.get("stdout"),
        "gazebo_version": gazebo.get("stdout"),
        "world_model_sha256": world_hash,
        "bridge_sha256": bridge_hash,
        "launch_sha256": launch_hash,
    }


def _normalized_run(
    short_id: str,
    raw: Mapping[str, Any],
    scenario: Mapping[str, Any],
    result: Mapping[str, Any],
    source_path: str,
    scenario_id: str,
    supporting: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    """Bind one result child to its own parent scenario and artifact context only."""
    row = _artifact_context(short_id, raw, scenario)
    row.update({field: result.get(field) for field in IDENTITY_FIELDS})
    row.update({"scenario_id": scenario_id, "source_json_path": source_path, "scenario_source_path": source_path.rsplit("/", 1)[0]})
    row["scenario_pass"] = scenario.get("pass")
    row["skill_result"] = result.get("skill_outcome")
    row["verification_result"] = result.get("verdict")
    error = result.get("error") if isinstance(result.get("error"), Mapping) else {}
    row["failure_code"] = error.get("code") or result.get("mismatch_code")
    row["recovery_decision"] = scenario.get("decision") or scenario.get("route")
    row["requires_failure_recovery"] = short_id == "SIM-009"
    row["requires_skill"] = short_id == "SIM-008"
    row["requires_verification"] = short_id == "SIM-008" or (
        scenario.get("backend") == "verification" and result.get("result") == "success"
    )
    row["verification_operational_failure"] = (
        scenario.get("backend") == "verification" and result.get("result") == "failure"
    )
    row["record_kind"] = "operation_run"
    row["requires_operation_identity"] = True
    row["semantic_outcome"] = {
        key: value for key, value in {
            "result": result.get("result"),
            "status": result.get("status"),
            "decision": scenario.get("expected_decision") or scenario.get("decision"),
            "outcome_kind": scenario.get("outcome_kind"),
            "lifecycle": scenario.get("expected_lifecycle"),
            "state_invariants": scenario.get("state_invariants"),
            "tolerances": scenario.get("measurements"),
        }.items() if value not in (None, "", [], {})
    }
    row["replay_applicable"] = short_id == "SIM-009" and scenario.get("backend") == "contract"
    row["physics_semantic_applicable"] = row.get("backend_profile") in {"gazebo", "mujoco", "mixed"}
    if row["replay_applicable"]:
        row["deterministic_replay"] = {
            "expected_decision": scenario.get("expected_decision"),
            "actual_decision": scenario.get("decision"),
            "expected_lifecycle": scenario.get("expected_lifecycle"),
            "actual_lifecycle": scenario.get("actual_lifecycle"),
        }
    if short_id == "SIM-004":
        bridge_hash, bridge_path = _asset(raw, "configs/simulation/sim004_navigation_proxy.yaml")
        launch_hash, launch_path = _asset(raw, "scripts/run_simulation_navigation.py")
        execution, execution_index = _sim004_execution(raw, result.get("action_id"))
        lifecycle = raw.get("bounded_lifecycle") if isinstance(raw.get("bounded_lifecycle"), Mapping) else {}
        cleanup = lifecycle.get("cleanup") if isinstance(lifecycle.get("cleanup"), Mapping) else {}
        simulator = row.setdefault("simulator_provenance", {})
        simulator.update({
            "bridge_sha256": bridge_hash,
            "launch_sha256": launch_hash,
            "simulation_time": None,
            "wall_time_ms": execution.get("duration_ms") if isinstance(execution, Mapping) else None,
            "bounded_execution": {
                "execution_bound_ms": execution.get("execution_bound_ms"),
                "cleanup_complete": cleanup.get("complete"),
                "cleanup_bound_ms": cleanup.get("bound_ms"),
            } if isinstance(execution, Mapping) else None,
        })
        authority = row.setdefault("provenance_authority", {})
        authority.update({
            "bridge_sha256": bridge_path,
            "launch_sha256": launch_path,
            "simulation_time": None,
            "wall_time_ms": f"/bounded_lifecycle/executions/{execution_index}/duration_ms" if execution_index is not None else None,
            "bounded_execution": f"/bounded_lifecycle/executions/{execution_index}" if execution_index is not None else None,
        })
        row["required_provenance_fields"] = (
            "ros2_identity", "gazebo_version", "world_model_sha256", "bridge_sha256", "launch_sha256",
            *(("simulation_time", "wall_time_ms", "bounded_execution") if execution is not None else ()),
        )
        row["physics_semantic_applicable"] = execution is not None
    elif short_id == "SIM-009":
        qualification = _supporting_backend_qualification(
            raw, result, row.get("backend_profile"), supporting
        )
        row["backend_qualification"] = qualification
        row["backend_qualification_authority"] = (
            f"/accepted_bindings/{qualification['source_task']}" if qualification else None
        )
        profile = row.get("backend_profile")
        physics_run = scenario.get("backend") in {"gazebo_navigation", "mujoco"}
        row["physics_semantic_applicable"] = physics_run
        if profile in {"gazebo", "mujoco"} and physics_run:
            row["simulator_provenance"] = {}
            row["required_provenance_fields"] = (
                "world_model_sha256", "simulation_time",
            )
            row["required_source_hash_fields"] = ("manifest_sha256", "run_config_sha256")
            row["required_backend_qualification_fields"] = (
                "source_task", "component_version", "accepted_commit", "evidence_path", "evidence_sha256"
            )
        else:
            row["simulator_provenance"] = {}
            row["required_provenance_fields"] = ()
            row["required_source_hash_fields"] = ("manifest_sha256",)
    return row


def extract_bound_runs(
    short_id: str,
    raw: Mapping[str, Any],
    supporting: Mapping[str, Mapping[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Extract only task-declared execution subtrees; never recursively search.

    Returned records retain their JSON pointer and identity source so a caller
    can reject incomplete traces without mixing fields across scenarios.
    """
    supporting = supporting or {}
    required = {"backend_profile", "mission_id", "request_id", "action_id", "trace_id"}
    if required.issubset(raw):
        envelope = dict(raw)
        scenarios = raw.get("scenarios")
        first = scenarios[0] if isinstance(scenarios, list) and scenarios and isinstance(scenarios[0], Mapping) else {}
        envelope["scenario_id"] = raw.get("scenario_id") or first.get("scenario_id") or short_id
        envelope["scenario_pass"] = all(first.get("state_invariants", {}).values()) if isinstance(first.get("state_invariants"), Mapping) else None
        envelope.setdefault("requires_failure_recovery", False)
        envelope.setdefault("requires_skill", False)
        envelope.setdefault("requires_verification", False)
        envelope["source_json_path"] = "/"
        envelope["scenario_source_path"] = "/scenarios/0" if first else "/"
        return [_record("/", str(envelope["scenario_id"]), envelope, envelope)]

    records: list[dict[str, Any]] = []
    scenarios = raw.get("scenarios")
    if short_id in {"SIM-004", "SIM-005", "SIM-009"} and isinstance(scenarios, list):
        for index, scenario in enumerate(scenarios):
            if not isinstance(scenario, Mapping):
                continue
            result = _scenario_result(scenario)
            scenario_id = scenario.get("id") or scenario.get("scenario")
            if not isinstance(scenario_id, str) or not scenario_id:
                continue
            # SIM-005 places its result scalar and correlation identity on the
            # scenario object itself.  That exact object is its declared run
            # subtree, so retain it and its direct JSON pointer rather than
            # searching for or constructing a replacement envelope.
            if short_id == "SIM-005" and result is None and all(
                field in scenario for field in ("mission_id", "request_id", "action_id", "result")
            ):
                normalized = _normalized_run(short_id, raw, scenario, scenario, f"/scenarios/{index}", scenario_id, supporting)
                records.append(_record(f"/scenarios/{index}", scenario_id, normalized, normalized))
                continue
            if short_id == "SIM-009" and result is None:
                normalized = _artifact_context(short_id, raw, scenario)
                normalized.update({
                    "scenario_id": scenario_id,
                    "source_json_path": f"/scenarios/{index}",
                    "scenario_source_path": f"/scenarios/{index}",
                    "scenario_pass": scenario.get("pass") is True,
                    "record_kind": "scenario_assertion",
                    "requires_operation_identity": False,
                    "required_identity_fields": (),
                    "requires_failure_recovery": False,
                    "requires_skill": False,
                    "requires_verification": False,
                    "recovery_decision": scenario.get("decision") or scenario.get("route"),
                    "replay_applicable": scenario.get("backend") == "contract",
                    "physics_semantic_applicable": False,
                    "simulator_provenance": {},
                    "required_provenance_fields": (),
                    "deterministic_replay": {
                        "expected_decision": scenario.get("expected_decision"),
                        "actual_decision": scenario.get("decision"),
                        "expected_lifecycle": scenario.get("expected_lifecycle"),
                        "actual_lifecycle": scenario.get("actual_lifecycle"),
                    },
                })
                records.append(_record(f"/scenarios/{index}", scenario_id, normalized, normalized))
                continue
            if result is None:
                continue
            key = next(
                (name for name in ("result", "timeout", "first_result", "retry_result", "verification", "reconciliation") if scenario.get(name) is result),
                None,
            )
            if key is None:
                continue
            path = f"/scenarios/{index}/{key}"
            normalized = _normalized_run(short_id, raw, scenario, result, path, scenario_id, supporting)
            records.append(_record(path, scenario_id, normalized, normalized))
        return records

    if short_id == "SIM-007":
        smoke = raw.get("profile_smoke")
        if not isinstance(smoke, list):
            return records
        for index, entry in enumerate(smoke):
            if not isinstance(entry, Mapping):
                continue
            profile = entry.get("profile")
            if not isinstance(profile, str) or not profile:
                continue
            normalized = _artifact_context(short_id, raw, entry)
            profiles = raw.get("profiles") if isinstance(raw.get("profiles"), Mapping) else {}
            profile_context = profiles.get(profile) if isinstance(profiles.get(profile), Mapping) else {}
            bounded = raw.get("bounded_lifecycle") if isinstance(raw.get("bounded_lifecycle"), Mapping) else {}
            normalized.update({field: entry.get(field) for field in IDENTITY_FIELDS})
            normalized.update({
                "simulation_only": bounded.get("physical_activity") is False,
                "scenario_id": profile,
                "source_json_path": f"/profile_smoke/{index}",
                "scenario_source_path": f"/profile_smoke/{index}",
                "scenario_pass": entry.get("mission_result") in {"success", "failure"},
                "record_kind": "profile_aggregate",
                "requires_operation_identity": False,
                "required_identity_fields": ("mission_id", "trace_id"),
                "action_ids": entry.get("action_ids"),
                "accepted_outcome": entry.get("mission_result"),
                "observed_outcome": entry.get("mission_result"),
                "failure_code": entry.get("failure_code"),
                "requires_failure_recovery": False,
                "recovery_decision": None,
                "requires_skill": False,
                "requires_verification": False,
                "replay_applicable": False,
                "physics_semantic_applicable": profile in {"navigation_physics", "manipulation_physics", "system"},
                "simulator_provenance": dict(profile_context),
                "required_provenance_fields": (),
                "artifact_context_paths": [f"/profile_smoke/{index}", f"/profiles/{profile}", "/bounded_lifecycle"],
            })
            records.append(_record(f"/profile_smoke/{index}", profile, normalized, normalized))
        return records

    if short_id == "SIM-008":
        execution = raw.get("execution")
        scenario = raw.get("scenario")
        if not isinstance(execution, Mapping) or not isinstance(scenario, Mapping):
            return records
        mission = execution.get("mission")
        steps = execution.get("steps")
        if not isinstance(mission, Mapping) or not isinstance(steps, list):
            return records
        vla = next((step for step in steps if isinstance(step, Mapping) and step.get("name") == "vla.execute"), None)
        final = next((step for step in steps if isinstance(step, Mapping) and step.get("name") == "final_verification"), None)
        if not isinstance(vla, Mapping) or not isinstance(final, Mapping):
            return records
        vla_result, final_result = vla.get("result"), final.get("result")
        if not isinstance(vla_result, Mapping) or not isinstance(final_result, Mapping):
            return records
        scenario_id = scenario.get("scenario_id")
        if not isinstance(scenario_id, str) or not scenario_id:
            return records
        envelope = {
            "simulation_only": True,
            "backend_profile": "gazebo",
            "mission_id": mission.get("mission_id"),
            "request_id": mission.get("request_id"),
            "action_id": vla_result.get("action_id"),
            "trace_id": mission.get("trace_id"),
            "skill_result": vla_result.get("skill_outcome"),
            "verification_result": final_result.get("verdict"),
            "source_hashes": {
                "scenario_config": scenario.get("config_sha256"),
                "world": scenario.get("world_sha256"),
            },
            "simulator_provenance": {
                "ros2_identity": raw.get("system_profile", {}).get("integrated_world") if isinstance(raw.get("system_profile"), Mapping) else None,
                "gazebo_version": raw.get("system_profile", {}).get("integrated_world") if isinstance(raw.get("system_profile"), Mapping) else None,
                "world_model_sha256": scenario.get("world_sha256"),
                "bridge_sha256": None,
                "launch_sha256": None,
                "simulation_time": None,
                "wall_time_ms": raw.get("execution", {}).get("duration_ms") if isinstance(raw.get("execution"), Mapping) else None,
                "bounded_execution": raw.get("execution", {}).get("lifecycle", {}).get("cleanup_complete") if isinstance(raw.get("execution", {}).get("lifecycle"), Mapping) else None,
            },
            "scenario_id": scenario_id,
            "source_json_path": "/execution",
            "scenario_source_path": "/execution",
            "scenario_pass": final_result.get("verdict") == "pass",
            "semantic_outcome": {
                "result": mission.get("result"),
                "status": mission.get("status"),
            },
            "requires_failure_recovery": False,
            "requires_skill": True,
            "requires_verification": True,
        }
        observation = final.get("observation") if isinstance(final.get("observation"), Mapping) else {}
        simulation_time = observation.get("simulation_time") if isinstance(observation, Mapping) else None
        if isinstance(simulation_time, Mapping):
            envelope["simulator_provenance"]["simulation_time"] = simulation_time.get("sec")
        records.append(_record("/execution", scenario_id, envelope, envelope))
    return records


def _accepted(value: Mapping[str, Any]) -> bool:
    return value.get("status") == "ACCEPT" or value.get("review_decision") == "ACCEPT"


def _valid_hash(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(char in "0123456789abcdef" for char in value.lower())


def _source_hashes_valid(value: Any) -> bool:
    return isinstance(value, Mapping) and bool(value) and all(_valid_hash(item) for item in value.values())


def _source_hash_failures(evidence: Mapping[str, Any]) -> list[str]:
    hashes = evidence.get("source_hashes")
    required = evidence.get("required_source_hash_fields")
    if required is None:
        return [] if _source_hashes_valid(hashes) else ["MISSING_SOURCE_CONFIG_HASHES"]
    if not isinstance(hashes, Mapping):
        return ["MISSING_SOURCE_CONFIG_HASHES"]
    return [
        f"MISSING_SOURCE_HASH:{field}"
        for field in required
        if not _valid_hash(hashes.get(field))
    ]


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


def _applicable_profile_failures(evidence: Mapping[str, Any]) -> list[str]:
    profile = evidence.get("backend_profile")
    provenance = evidence.get("simulator_provenance")
    explicit = evidence.get("required_provenance_fields")
    if explicit is None:
        return _profile_failures(profile, provenance)
    if profile not in {"deterministic", "verification", "gazebo", "mujoco", "mixed"}:
        return ["MISSING_BACKEND_PROFILE"]
    if not isinstance(provenance, Mapping):
        return ["MISSING_SIMULATOR_PROVENANCE"]
    failures = [f"MISSING_{key.upper()}" for key in explicit if provenance.get(key) in (None, "", {}, [])]
    qualification_required = evidence.get("required_backend_qualification_fields")
    if qualification_required is not None:
        qualification = evidence.get("backend_qualification")
        if not isinstance(qualification, Mapping):
            failures.append("MISSING_BACKEND_QUALIFICATION")
        else:
            failures.extend(
                f"MISSING_BACKEND_QUALIFICATION:{key}"
                for key in qualification_required
                if qualification.get(key) in (None, "", {}, [])
            )
    return failures


def _correlation_failures(evidence: Mapping[str, Any]) -> list[str]:
    explicit_identity = evidence.get("required_identity_fields")
    required = list(explicit_identity) if isinstance(explicit_identity, (list, tuple)) else list(IDENTITY_FIELDS)
    if evidence.get("requires_skill"):
        required.append("skill_result")
    if evidence.get("requires_verification"):
        required.append("verification_result")
    if evidence.get("requires_failure_recovery"):
        required.extend(("failure_code", "recovery_decision"))
    failures = [f"MISSING_{field.upper()}" for field in required if evidence.get(field) in (None, "", [], {})]
    if required and any(evidence.get(field) in (None, "", [], {}) for field in required):
        failures.append("INCOMPLETE_CORRELATION_IDENTITY")
    return failures


def _scenario_failures(evidence: Mapping[str, Any]) -> list[str]:
    """Validate the one normalized scenario row, not an artifact-level list."""
    scenario_id = evidence.get("scenario_id")
    if not isinstance(scenario_id, str) or not scenario_id:
        return ["UNBOUND_SCENARIO"]
    if evidence.get("accepted_outcome") is not None and evidence.get("accepted_outcome") != evidence.get("observed_outcome"):
        return [f"SCENARIO_OUTCOME_MISMATCH:{scenario_id}"]
    if evidence.get("scenario_pass") is False:
        return [f"SCENARIO_ASSERTION_FAILED:{scenario_id}"]
    return []


def _run_source_summary(run: Mapping[str, Any]) -> dict[str, Any]:
    evidence = run["envelope"]
    keys = (
        "record_kind", "backend_profile", "scenario_source_path", "action_ids",
        "source_hashes", "simulator_provenance", "provenance_authority",
        "backend_qualification", "backend_qualification_authority",
        "accepted_outcome", "observed_outcome", "failure_code",
        "verification_result", "verification_operational_failure", "recovery_decision",
    )
    summary = {
        "source_json_path": run["source_json_path"],
        "scenario_id": run["scenario_id"],
        "identity": run["identity"],
    }
    summary.update({key: evidence.get(key) for key in keys if key in evidence})
    return summary


def _deterministic_replay(evidences: list[Mapping[str, Any]]) -> dict[str, Any]:
    rows = [
        item for item in evidences
        if item.get("backend_profile") == "deterministic" and item.get("replay_applicable", True)
    ]
    failures: list[str] = []
    for item in rows:
        replay = item.get("deterministic_replay")
        if not isinstance(replay, Mapping) or replay.get("expected_decision") != replay.get("actual_decision") or replay.get("expected_lifecycle") != replay.get("actual_lifecycle"):
            failures.append("DETERMINISTIC_REPLAY_MISMATCH")
    if not rows:
        failures.append("NO_VALIDATED_DETERMINISTIC_RUNS")
    return {"status": "PASS" if rows and not failures else "BLOCKED", "criterion": "equivalent decisions and lifecycle outcomes", "failures": failures}


def _physics_semantic(evidences: list[Mapping[str, Any]]) -> dict[str, Any]:
    rows = [
        item for item in evidences
        if item.get("backend_profile") in {"gazebo", "mujoco", "mixed"}
        and item.get("physics_semantic_applicable", True)
    ]
    failures = [failure for item in rows for failure in _scenario_failures(item)]
    profiles = {item.get("backend_profile") for item in rows}
    if not rows:
        failures.append("NO_VALIDATED_PHYSICS_RUNS")
    for profile in ("gazebo", "mujoco"):
        if profile not in profiles:
            failures.append(f"MISSING_REQUIRED_PHYSICS_PROFILE:{profile}")
    return {"status": "PASS" if rows and not failures else "BLOCKED", "criterion": "outcome, lifecycle, invariants, and declared tolerances", "failures": failures}


def _q01_physics_rows(linked_rows: list[Mapping[str, Any]]) -> tuple[list[dict[str, Any]], list[str]]:
    """Compare Q01 actual observations to, but never coalesce with, historical oracles."""
    rows: list[dict[str, Any]] = []
    failures: list[str] = []
    for linked in linked_rows:
        oracle = linked.get("historical_oracle")
        observation = linked.get("qualification_observation")
        if not isinstance(oracle, Mapping) or not isinstance(observation, Mapping):
            failures.append("INVALID_LINKED_AUTHORITY")
            continue
        expected_profile = oracle.get("envelope", {}).get("backend_profile") if isinstance(oracle.get("envelope"), Mapping) else None
        if expected_profile not in {"gazebo", "mujoco"} or observation.get("backend_profile") != expected_profile:
            failures.append(f"Q01_ORACLE_PROFILE_MISMATCH:{linked.get('subject_id')}")
            continue
        actual = observation.get("semantic_outcome")
        expected = oracle.get("envelope", {}).get("semantic_outcome") if isinstance(oracle.get("envelope"), Mapping) else None
        if (not isinstance(actual, Mapping) or not isinstance(expected, Mapping)
                or not isinstance(actual.get("result"), str) or not isinstance(actual.get("status"), str)):
            failures.append(f"Q01_INVALID_SEMANTIC_OUTCOME:{linked.get('subject_id')}")
            continue
        comparable = ("result", "status", "decision", "outcome_kind", "lifecycle", "state_invariants", "tolerances")
        mismatches = [key for key in comparable if expected.get(key) not in (None, "", [], {}) and actual.get(key) != expected.get(key)]
        if mismatches:
            failures.append(f"Q01_SEMANTIC_MISMATCH:{linked.get('subject_id')}:{','.join(mismatches)}")
            continue
        if not all(
            isinstance(value, Mapping) and value
            for value in (observation.get("configuration_provenance"), observation.get("world_model_provenance"))
        ):
            failures.append(f"Q01_PROVENANCE_MISMATCH:{linked.get('subject_id')}")
            continue
        row = dict(observation)
        row.update({"scenario_id": oracle.get("envelope", {}).get("scenario_id"), "scenario_pass": True})
        rows.append(row)
    return rows, failures


def build_regression_evidence(root: Path) -> dict[str, Any]:
    """Build a normalized, accepted-artifact-only regression record."""
    index: list[dict[str, Any]] = []
    valid_evidence: list[Mapping[str, Any]] = []
    supporting: dict[str, Mapping[str, Any]] = {}
    q01: dict[str, Any] | None = None
    q01_failures: list[str] = []
    try:
        q01 = resolve_q01_qualification(root)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        q01_failures.append(str(exc) or "Q01_UNRESOLVABLE")
    for supporting_id in ("SIM-004", "SIM-005"):
        try:
            supporting_acceptance = _load_json(root / "results/reviews" / f"{supporting_id}_acceptance.json")
            supporting[supporting_id] = resolve_accepted_evidence(root, supporting_id, supporting_acceptance)
        except (OSError, ValueError, json.JSONDecodeError):
            # The corresponding canonical source row records the authoritative
            # failure.  Cross-predecessor qualification simply remains absent.
            pass
    for short_id in SOURCE_TASKS:
        acceptance_path = root / "results/reviews" / f"{short_id}_acceptance.json"
        row: dict[str, Any] = {"short_task_id": short_id, "acceptance_path": str(acceptance_path.relative_to(root)), "status": "PASS", "failures": []}
        try:
            acceptance = _load_json(acceptance_path)
            row["acceptance_sha256"] = sha256(acceptance_path)
            if acceptance.get("task_id") != f"TASK-{short_id}" or not _accepted(acceptance):
                row["failures"].append("INVALID_ACCEPTANCE")
            resolved = resolve_accepted_evidence(root, short_id, acceptance)
            row.update(accepted_commit=resolved["accepted_commit"], evidence_path=resolved["evidence_path"], evidence_sha256=resolved["evidence_sha256"])
            runs = extract_bound_runs(short_id, resolved["evidence"], supporting)
            if short_id in {"SIM-008", "SIM-009"}:
                row["declared_scenario_ids"] = _declared_scenario_ids(short_id, resolved["evidence"])
            run_required = short_id in RUN_EXTRACTOR_TASKS
            row["run_extraction"] = {
                "required": run_required,
                # Aggregate/provenance artifacts are valid source bindings but
                # are not declared execution sources.  They must not acquire a
                # run failure merely because no run exists inside their blob.
                "status": "PASS" if runs else ("BLOCKED" if run_required else "NOT_REQUIRED"),
                "failures": [] if runs or not run_required else ["NO_EXTRACTABLE_RUNS"],
            }
            if runs:
                row["run_sources"] = [_run_source_summary(run) for run in runs]
            run_validation_failures: list[str] = []
            for position, run in enumerate(runs):
                evidence = run["envelope"]
                run_failures: list[str] = []
                if evidence.get("simulation_only") is not True: run_failures.append("MISSING_SIMULATION_ONLY_LABEL")
                run_failures.extend(_source_hash_failures(evidence))
                run_failures.extend(_correlation_failures(evidence))
                run_failures.extend(_applicable_profile_failures(evidence))
                run_failures.extend(_scenario_failures(evidence))
                run_validation_failures.extend(f"RUN[{position}]:{failure}" for failure in run_failures)
                if not run_failures and not (
                    short_id in {"SIM-008", "SIM-009"} and evidence.get("physics_semantic_applicable")
                ):
                    valid_evidence.append(evidence)
            if runs:
                row["run_validation"] = {
                    "status": "PASS" if not run_validation_failures else "BLOCKED",
                    "failures": run_validation_failures,
                }
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            row["failures"].append(str(exc) or f"UNREADABLE_SOURCE:{type(exc).__name__}")
        if row["failures"]: row["status"] = "FAIL"
        index.append(row)
    deterministic = _deterministic_replay(valid_evidence)
    linked_rows = q01.get("qualification_subjects", []) if q01 else []
    q01_physics, physics_failures = _q01_physics_rows(linked_rows)
    physics = _physics_semantic(q01_physics)
    physics["failures"] = [*physics["failures"], *physics_failures, *q01_failures]
    physics["status"] = "PASS" if not physics["failures"] else "BLOCKED"
    normal = next((row for row in index if row["short_task_id"] == "SIM-008"), None)
    failure = next((row for row in index if row["short_task_id"] == "SIM-009"), None)
    def has_extracted_runs(row: Mapping[str, Any] | None) -> bool:
        extraction = row.get("run_extraction") if isinstance(row, Mapping) else None
        return isinstance(extraction, Mapping) and extraction.get("status") == "PASS"

    coverage_failures: list[str] = []
    for coverage_row in (normal, failure):
        if not coverage_row or not has_extracted_runs(coverage_row):
            coverage_failures.append("UNBOUND_NORMAL_OR_FAILURE_SUITE")
            continue
        declared = set(coverage_row.get("declared_scenario_ids", []))
        extracted = {
            source.get("scenario_id")
            for source in coverage_row.get("run_sources", [])
            if isinstance(source, Mapping) and isinstance(source.get("scenario_id"), str)
        }
        for missing in sorted(declared - extracted):
            coverage_failures.append(f"MISSING_MANDATORY_SCENARIO:{coverage_row['short_task_id']}:{missing}")
    required_failure_classification = classify_required_run_failures(index, q01)
    required_run_failures = [
        entry for entry in required_failure_classification["entries"]
        if entry["classification"] == "STILL_BLOCKING"
    ]
    for row in index:
        if row["short_task_id"] in RUN_EXTRACTOR_TASKS and not has_extracted_runs(row):
            required_run_failures.append({
                "source_task": row["short_task_id"],
                "failure": "NO_EXTRACTABLE_RUNS",
                "classification": "STILL_BLOCKING",
            })
    ready = (
        all(row["status"] == "PASS" for row in index)
        and not required_run_failures
        and not coverage_failures
        and q01 is not None
        and deterministic["status"] == physics["status"] == "PASS"
    )
    return {"schema_version": "1.0", "task_id": "TASK-SIM-010", "simulation_only": True, "claim_scope": "Simulation evidence only; no physical or production performance claim.", "accepted_source_index": index, "required_run_failure_classification": required_failure_classification, "q01_qualification_binding": q01 or {"status": "BLOCKED", "failures": q01_failures}, "deterministic_replay": deterministic, "physics_semantic_regression": physics, "normal_failure_suite_coverage": {"status": "PASS" if not coverage_failures else "BLOCKED", "failures": coverage_failures}, "task_specific_result": "SIM_OBSERVABILITY_REGRESSION_READY" if ready else "SIM_OBSERVABILITY_REGRESSION_BLOCKED"}
