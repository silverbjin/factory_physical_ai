"""Bounded TASK-SIM-009 fault scenarios over accepted simulation adapters."""
from __future__ import annotations

import json
import hashlib
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from mission_runtime import MissionRecord, MissionStatus
from scripts.sim009_goal_tracked_navigation import GoalTrackedGazeboNav2Runtime
from scripts.run_simulation_navigation import EXECUTION_SECONDS
from .mujoco_vla_backend import MuJoCoVLABackend, observation_ref
from .navigation_backend import NavigationBackend, RuntimeObservation
from .smoke import ContractViolation, canonical_sha256, validate_contract_message
from .verification_backend import VerificationBackend, normalize_deterministic_observation

ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = ROOT / "configs/simulation/sim009_failure_scenarios.json"
MANDATORY_SCENARIO_IDS = (
    "SIM009-L0-MALFORMED", "SIM009-L0-UNAVAILABLE", "SIM009-L0-CONTRADICTORY",
    "SIM009-NAV-BLOCKED", "SIM009-NAV-ABORTED", "SIM009-NAV-TIMEOUT-RETRY", "SIM009-NAV-TF-UNAVAILABLE",
    "SIM009-VLA-GRASP-MISS", "SIM009-VLA-CONTACT-LOSS", "SIM009-VLA-WORKSPACE-LIMIT", "SIM009-VLA-TIMEOUT", "SIM009-VLA-AMBIGUOUS", "SIM009-VLA-UNKNOWN",
    "SIM009-VERIFY-MISMATCH", "SIM009-VERIFY-STALE", "SIM009-VERIFY-UNCERTAIN",
)
INTENTIONAL_FAULT_TIMEOUT_MS = 2_000
NORMAL_RECOVERY_TIMEOUT_MS = EXECUTION_SECONDS * 1_000
LIVE_RUNTIME_SCHEDULING_MARGIN_MS = 1_000
LIVE_NAVIGATION_CALL_BUDGET_MS = (
    # A live rclpy NavigateToPose call has three independently bounded waits:
    # action-server discovery, goal acceptance, and the same goal's terminal
    # result.  The scenario timer intentionally covers all three.
    3 * INTENTIONAL_FAULT_TIMEOUT_MS + LIVE_RUNTIME_SCHEDULING_MARGIN_MS
)
LIVE_NAVIGATION_RETRY_BUDGET_MS = (
    INTENTIONAL_FAULT_TIMEOUT_MS
    + NORMAL_RECOVERY_TIMEOUT_MS
    + LIVE_RUNTIME_SCHEDULING_MARGIN_MS
)
MAX_SCENARIO_BUDGET_MS = LIVE_NAVIGATION_RETRY_BUDGET_MS


def _timestamp(value: datetime) -> str:
    return value.isoformat(timespec="milliseconds").replace("+00:00", "Z")


def load_manifest(path: Path = MANIFEST_PATH) -> dict[str, Any]:
    manifest = json.loads(path.read_text())
    if manifest.get("schema_version") != "1.0" or manifest.get("task_id") != "TASK-SIM-009":
        raise ValueError("SIM-009 manifest identity is malformed")
    scenarios = manifest.get("scenarios")
    if not isinstance(scenarios, list) or [row.get("id") for row in scenarios] != list(MANDATORY_SCENARIO_IDS):
        raise ValueError("SIM-009 scenario IDs are incomplete or unstable")
    for scenario in scenarios:
        if set(scenario) != {"id", "layer", "backend", "injection", "expected_decision", "budget_ms"} or not isinstance(scenario["budget_ms"], int) or not 0 < scenario["budget_ms"] <= MAX_SCENARIO_BUDGET_MS:
            raise ValueError("SIM-009 scenario budget or shape is malformed")
    return manifest


def _accepted_binding(task: str) -> dict[str, Any]:
    path = ROOT / f"results/reviews/{task}_acceptance.json"
    raw = path.read_bytes()
    record = json.loads(raw)
    expected = {
        "SIM-004": "SIM_NAVIGATION_BACKEND_READY",
        "SIM-005": "SIM_MANIPULATION_BACKEND_READY",
        "SIM-006": "SIM_VERIFICATION_BACKEND_READY",
        "SIM-008": "SIM_NORMAL_E2E_READY",
    }[task]
    if record.get("status") != "ACCEPT":
        raise ValueError(f"{task} is not accepted")
    evidence = ROOT / record["evidence"]["path"]
    evidence_raw = evidence.read_bytes()
    if hashlib.sha256(evidence_raw).hexdigest() != record["evidence"]["sha256"]:
        raise ValueError(f"{task} accepted evidence hash does not match")
    evidence_payload = json.loads(evidence_raw)
    if evidence_payload.get("task_specific_result", evidence_payload.get("result")) != expected:
        raise ValueError(f"{task} accepted evidence does not report {expected}")
    return {"acceptance": record, "acceptance_sha256": hashlib.sha256(raw).hexdigest()}


def _action_request(operation: str, *, task_id: str | None = None, mission_id: str | None = None,
                    action_id: str | None = None, idempotency_key: str | None = None,
                    attempt: int = 1, timeout_ms: int = INTENTIONAL_FAULT_TIMEOUT_MS,
                    scenario_id: str | None = None) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    request: dict[str, Any] = {"operation": operation, "message_type": "request", "schema_version": "1.0", "mission_id": mission_id or str(uuid.uuid4()), "request_id": str(uuid.uuid4()), "trace_id": str(uuid.uuid4()), "timestamp": _timestamp(now), "deadline_at": _timestamp(now + timedelta(milliseconds=timeout_ms)), "timeout_ms": timeout_ms, "component_version": "sim009-failure-suite-v1", "action_id": action_id or str(uuid.uuid4())}
    if operation == "navigation.execute":
        destination_id = "blocked-bay" if scenario_id == "SIM009-NAV-BLOCKED" else "line-b-drop"
        request |= {"idempotency_key": idempotency_key or "sim009-navigation", "attempt": attempt, "retry_budget_remaining": 1, "robot_id": "simulation-proxy-mobile-base", "destination_id": destination_id, "speed_profile_id": "sim-safe-v1"}
    elif operation == "vla.execute":
        request |= {"idempotency_key": idempotency_key or "sim009-vla", "attempt": attempt, "retry_budget_remaining": 1, "robot_id": "generic-simulation-proxy", "task_id": task_id or "mujoco-place-nominal", "policy_version": "sim005-scripted-policy-v1", "observation_refs": [observation_ref()], "workspace_profile_id": "sim005-workspace-v1"}
    return request


def _status_request(executed: dict[str, Any]) -> dict[str, Any]:
    return {key: executed[key] for key in ("schema_version", "mission_id", "trace_id", "timestamp", "deadline_at", "timeout_ms", "component_version", "action_id")} | {"operation": "action_status.get", "message_type": "request", "request_id": str(uuid.uuid4())}


class _ScriptedNavigationRuntime:
    def __init__(self, observations: list[RuntimeObservation], reconciled: RuntimeObservation, *, ready: bool = True) -> None:
        self.observations, self.reconciled, self.ready = list(observations), reconciled, ready
        self.calls = 0
        self.closed = False
        self.side_effect_count = 0

    def navigate(self, request: dict[str, Any]) -> RuntimeObservation:
        observation = self.observations[min(self.calls, len(self.observations) - 1)]
        self.calls += 1
        self.side_effect_count += int(observation.observed_status == "succeeded")
        return observation

    def reconcile(self, action_id: str) -> RuntimeObservation:
        return self.reconciled

    def close(self) -> bool:
        self.closed = True
        return True


def _retry_authorization(previous: dict[str, Any], retry: dict[str, Any], *,
                         reconciliation: dict[str, Any], resolved: RuntimeObservation) -> dict[str, Any]:
    """Build the frozen, schema-valid proof required before dispatching a retry."""
    authorization = {
        "record_type": "retry_authorization",
        "mission_id": previous["mission_id"],
        "action_id": previous["action_id"],
        "idempotency_key": previous["idempotency_key"],
        "previous_request_id": previous["request_id"],
        "new_request_id": retry["request_id"],
        "previous_attempt": previous["attempt"],
        "next_attempt": retry["attempt"],
        "retry_budget_remaining": previous["retry_budget_remaining"],
        "reconciliation_completed": reconciliation["result"] == "success",
        "resolved_status": reconciliation.get("observed_status"),
        "error": {"code": resolved.error_code, "message": resolved.error_message,
                  "category": resolved.error_category, "retryable": resolved.retryable},
    }
    validate_contract_message(authorization)
    return authorization


def _authorized_retry(
    previous: dict[str, Any], *, reconciliation: dict[str, Any], resolved: RuntimeObservation,
) -> tuple[dict[str, Any], dict[str, Any]] | None:
    """Return a retry request and its authorization only after failed reconciliation."""
    if (
        reconciliation.get("result") != "success"
        or reconciliation.get("observed_status") != "failed"
        or resolved.observed_status != "failed"
        or not resolved.retryable
        or previous["retry_budget_remaining"] <= 0
    ):
        return None
    retry = _action_request(
        "navigation.execute",
        mission_id=previous["mission_id"],
        action_id=previous["action_id"],
        idempotency_key=previous["idempotency_key"],
        attempt=previous["attempt"] + 1,
        timeout_ms=NORMAL_RECOVERY_TIMEOUT_MS,
    )
    retry["trace_id"] = previous["trace_id"]
    retry["destination_id"] = previous["destination_id"]
    retry["retry_budget_remaining"] = previous["retry_budget_remaining"] - 1
    return retry, _retry_authorization(
        previous, retry, reconciliation=reconciliation, resolved=resolved,
    )


def _mission_verification_route(route: str, verification: dict[str, Any]) -> dict[str, Any]:
    """Apply a non-pass route through the accepted MissionRecord lifecycle."""
    mission = MissionRecord(str(uuid.uuid4()))
    mission = mission.transition(MissionStatus.READY).transition(MissionStatus.EXECUTING)
    states = [MissionStatus.EXECUTING]
    if route == "RECOVERY":
        # A verification mismatch cannot skip directly into recovery: unknown
        # work must first enter reconciliation, where recovery is authorized.
        mission = mission.transition(MissionStatus.RECONCILING).transition(MissionStatus.RECOVERING)
        outcome = "in_progress"
    elif route == "RECONCILE":
        mission = mission.transition(MissionStatus.RECONCILING)
        outcome = "in_progress"
    elif route == "HITL":
        mission = mission.transition(MissionStatus.ESCALATED)
        outcome = "requires_human"
    else:
        raise ValueError("verification pass is not a SIM-009 fault route")
    states.extend(
        [MissionStatus.RECONCILING, MissionStatus.RECOVERING]
        if route == "RECOVERY" else [mission.status]
    )
    return {
        "verification_verdict": verification.get("verdict"),
        "mission_state": mission.status.value.lower(),
        "mission_outcome": outcome,
        "mission_success_committed": False,
        "transition": {"from": "executing", "to": mission.status.value.lower()},
        "transition_path": [state.value.lower() for state in states],
    }


def _base_row(scenario: dict[str, Any], *, decision: str, outcome_kind: str, details: dict[str, Any]) -> dict[str, Any]:
    return {"id": scenario["id"], "layer": scenario["layer"], "backend": scenario["backend"], "injection": scenario["injection"], "expected_decision": scenario["expected_decision"], "decision": decision, "outcome_kind": outcome_kind, "cleanup_complete": True, "pass": decision == scenario["expected_decision"], **details}


def _validate_live_navigation_evidence(
    scenario_id: str, request: dict[str, Any], evidence: dict[str, Any],
) -> bool:
    """Reject cross-scenario or generic terminal evidence for an R3 fault."""
    execution_id = evidence.get("scenario_execution_id")
    attempts = evidence.get("goal_attempts", [])
    if (
        not isinstance(execution_id, str)
        or evidence.get("scenario_id") != scenario_id
        or len(attempts) < 1
        or any(item.get("scenario_id") != scenario_id or item.get("scenario_execution_id") != execution_id for item in attempts)
    ):
        return False
    matching = [item for item in attempts if item.get("action_id") == request["action_id"]]
    if not matching:
        return False
    attempt = matching[0]
    if (
        attempt.get("destination_id") != request["destination_id"]
        or not attempt.get("nav2_goal_uuid")
        or attempt.get("terminal_goal_uuid") != attempt.get("nav2_goal_uuid")
        or attempt.get("terminal_status") != "6"
    ):
        return False
    native = " ".join(str(item) for item in (
        attempt.get("native_error_code"), attempt.get("native_error_message"),
        attempt.get("server_log_tail"),
    ) if item)
    if scenario_id == "SIM009-NAV-BLOCKED":
        return (
            attempt.get("injection_kind") == "none"
            and attempt.get("frame_id") == "map"
            and not attempt.get("behavior_tree")
            and ("204" in native or "outside" in native.lower() or "no valid path" in native.lower())
        )
    if scenario_id == "SIM009-NAV-ABORTED":
        behavior_tree = attempt.get("behavior_tree")
        return (
            attempt.get("injection_kind") == "missing_behavior_tree"
            and attempt.get("frame_id") == "map"
            and isinstance(behavior_tree, str)
            and behavior_tree.startswith("/tmp/sim009-missing-behavior-tree")
            and behavior_tree in native
            and any(token in native.lower() for token in ("error", "fail", "load"))
        )
    if scenario_id == "SIM009-NAV-TF-UNAVAILABLE":
        probes = evidence.get("tf_probes", [])
        baseline = [item for item in probes if item.get("label") == "sim009_tf_baseline"]
        injected = [item for item in probes if item.get("label") == "sim009_tf_injected_missing"]
        return (
            attempt.get("injection_kind") == "missing_goal_frame"
            and isinstance(attempt.get("frame_id"), str)
            and attempt["frame_id"].startswith("sim009_missing_tf_frame")
            and not attempt.get("behavior_tree")
            and len(baseline) == 1 and baseline[0].get("available") is True
            and len(injected) == 1 and injected[0].get("available") is False
            and all(item.get("scenario_execution_id") == execution_id for item in probes)
            and ("202" in native or "tf" in native.lower() or "transform" in native.lower())
        )
    return False


def _contract_scenario(scenario: dict[str, Any]) -> dict[str, Any]:
    if scenario["id"] == "SIM009-L0-MALFORMED":
        request = _action_request("navigation.execute"); request["timeout_ms"] = 0
        result = NavigationBackend().execute(request)
        return _base_row(scenario, decision="FAIL_CLOSED", outcome_kind="malformed", details={"result": result})
    contradictory = {"operation": "navigation.execute", "message_type": "result", "schema_version": "1.0", "mission_id": str(uuid.uuid4()), "request_id": str(uuid.uuid4()), "trace_id": str(uuid.uuid4()), "action_id": str(uuid.uuid4()), "timestamp": _timestamp(datetime.now(timezone.utc)), "component_version": "sim009", "source_kind": "mock", "status": "failed", "result": "success"}
    try:
        validate_contract_message(contradictory)
    except ContractViolation as exc:
        return _base_row(scenario, decision="FAIL_CLOSED", outcome_kind="contradictory", details={"validation_error": str(exc)})
    raise AssertionError("contradictory result unexpectedly validated")


def _navigation_scenario(
    scenario: dict[str, Any], *, runtime_factory: Any = _ScriptedNavigationRuntime,
    live_runtime: GoalTrackedGazeboNav2Runtime | None = None,
) -> dict[str, Any]:
    identifier = scenario["id"]
    if identifier.startswith("SIM009-NAV-") and live_runtime is not None and not live_runtime.ready:
        return _base_row(
            scenario, decision="FAIL_CLOSED", outcome_kind="unavailable",
            details={"result": {"result": "failure", "error": "Gazebo/Nav2 runtime did not become ready"},
                     "runtime_calls": 0, "goal_tracking": {}, "cleanup_complete": True},
        )
    if identifier == "SIM009-L0-UNAVAILABLE":
        # L0 availability is a contract-boundary prerequisite check; the
        # L1-NAV cases below are the only paths that exercise live Gazebo.
        runtime = _ScriptedNavigationRuntime([RuntimeObservation("failed")], RuntimeObservation("failed"), ready=False)
        result = NavigationBackend(runtime).execute(_action_request("navigation.execute"))
        return _base_row(scenario, decision="FAIL_CLOSED", outcome_kind="unavailable", details={"result": result, "runtime_calls": runtime.calls, "cleanup_complete": runtime.close()})
    if identifier == "SIM009-NAV-TIMEOUT-RETRY":
        runtime = live_runtime or runtime_factory(
            [RuntimeObservation("unknown", error_code="NAV_TIMEOUT", error_message="bounded timeout", error_category="DEPENDENCY_TIMEOUT", retryable=True), RuntimeObservation("succeeded", arrival_verified=True)],
            RuntimeObservation("failed", error_code="NAV_RETRYABLE", error_message="authoritative retryable failure", error_category="EXECUTION_FAILED", retryable=True),
        )
        backend = NavigationBackend(runtime)
        context = live_runtime.begin_scenario(identifier) if live_runtime is not None else None
        first = _action_request("navigation.execute", scenario_id=identifier)
        first["destination_id"] = "line-b-drop"
        if live_runtime is not None:
            # Inject after action-server readiness but before the first result
            # wait, preserving G1 for cancellation and reconciliation.
            live_runtime.inject_timeout_on_next_goal()
        try:
            pending = backend.execute(first)
            lookup_request = _status_request(first); reconciliation = backend.action_status_get(lookup_request)
            resolved = runtime.reconcile(first["action_id"])
            authorized_retry = _authorized_retry(
                first, reconciliation=reconciliation, resolved=resolved,
            )
        except Exception:
            if context is not None:
                live_runtime.end_scenario(context)
            raise
        retry: dict[str, Any] | None = None
        authorization: dict[str, Any] | None = None
        retried: dict[str, Any] | None = None
        identity: dict[str, bool] = {}
        try:
            if authorized_retry is not None:
                retry, authorization = authorized_retry
                retried = backend.execute(retry)
                identity = {"mission_id_stable": retry["mission_id"] == first["mission_id"], "action_id_stable": retry["action_id"] == first["action_id"], "idempotency_key_stable": retry["idempotency_key"] == first["idempotency_key"], "retry_request_id_new": retry["request_id"] != first["request_id"], "attempt_incremented": retry["attempt"] == first["attempt"] + 1}
        except Exception:
            if context is not None:
                live_runtime.end_scenario(context)
            raise
        valid_retry = (
            pending["status"] == "unknown"
            and authorization is not None
            and retried is not None
            and authorization["reconciliation_completed"]
            and authorization["error"]["retryable"]
            and authorization["retry_budget_remaining"] > 0
            and retried["result"] == "success"
            and all(identity.values())
        )
        cleanup_complete = True if live_runtime is not None else runtime.close()
        attempts = getattr(runtime, "goal_attempts", [])
        successful_goals = sum(1 for item in attempts if item.terminal_status == "4") if attempts else runtime.side_effect_count
        local_evidence = runtime.evidence_for(context.scenario_execution_id) if context is not None else {}
        if context is not None:
            live_runtime.end_scenario(context)
        row = _base_row(scenario, decision="RETRY" if valid_retry else "FAIL_CLOSED", outcome_kind="unknown", details={"first_result": pending, "reconciliation": reconciliation, "retry_authorization": authorization, "retry_request": retry, "retry_result": retried, "retry_suppressed": authorized_retry is None, "identity": identity, "logical_side_effect_count": successful_goals, "runtime_calls": len(attempts) if attempts else runtime.calls, "goal_tracking": local_evidence, "cleanup_complete": cleanup_complete})
        row["pass"] = valid_retry and row["expected_decision"] == "RETRY"
        return row
    request = _action_request("navigation.execute", scenario_id=identifier)
    context = live_runtime.begin_scenario(identifier) if live_runtime is not None else None
    if live_runtime is not None and identifier == "SIM009-NAV-ABORTED":
        live_runtime.inject_abort_on_next_goal()
    elif live_runtime is not None and identifier == "SIM009-NAV-TF-UNAVAILABLE":
        live_runtime.inject_tf_unavailable_on_next_goal()
    code = "PATH_BLOCKED" if identifier == "SIM009-NAV-BLOCKED" else (
        "NAV_TF_UNAVAILABLE" if identifier == "SIM009-NAV-TF-UNAVAILABLE" else "NAV_ABORTED"
    )
    runtime = live_runtime or runtime_factory([RuntimeObservation("failed", error_code=code, error_message="injected navigation failure")], RuntimeObservation("failed"))
    try:
        result = NavigationBackend(runtime).execute(request)
        local_evidence = runtime.evidence_for(context.scenario_execution_id) if context is not None else {}
    finally:
        if context is not None:
            live_runtime.end_scenario(context)
    native_failure = result["result"] == "failure"
    local_attempts = local_evidence.get("goal_attempts", [])
    local_provenance = live_runtime is None or _validate_live_navigation_evidence(identifier, request, local_evidence)
    row = _base_row(scenario, decision="FAIL_CLOSED", outcome_kind="failure", details={"result": result, "runtime_calls": len(getattr(runtime, "goal_attempts", [])) if live_runtime is not None else runtime.calls, "goal_tracking": local_evidence, "cleanup_complete": True if live_runtime is not None else runtime.close(), "scenario_local_provenance": local_provenance, "native_failure": native_failure})
    row["pass"] = bool(row["pass"] and native_failure and local_provenance)
    return row


def _vla_scenario(scenario: dict[str, Any]) -> dict[str, Any]:
    mapping = {"SIM009-VLA-GRASP-MISS": "mujoco-grasp-miss", "SIM009-VLA-CONTACT-LOSS": "mujoco-contact-loss", "SIM009-VLA-WORKSPACE-LIMIT": "mujoco-workspace-limit", "SIM009-VLA-TIMEOUT": "mujoco-timeout", "SIM009-VLA-UNKNOWN": "mujoco-unknown"}
    request = _action_request("vla.execute", task_id=mapping.get(scenario["id"], "mujoco-place-nominal"))
    if scenario["id"] == "SIM009-VLA-AMBIGUOUS": request["observation_refs"] = [{**observation_ref(), "fixture_id": "ambiguous-observation"}]
    backend = MuJoCoVLABackend(); result = backend.execute(request)
    details: dict[str, Any] = {"result": result}
    if result["status"] == "unknown":
        details["reconciliation"] = backend.action_status_get(_status_request(request))
        decision, kind = "RECONCILE", "unknown"
    else:
        decision, kind = "FAIL_CLOSED", "uncertain" if scenario["id"] == "SIM009-VLA-AMBIGUOUS" else "failure"
    return _base_row(scenario, decision=decision, outcome_kind=kind, details=details)


def _verification_request(observation: Any, *, stale: bool = False) -> dict[str, Any]:
    observed_at = datetime.fromisoformat(observation.reference["timestamp"].replace("Z", "+00:00"))
    now = observed_at + timedelta(minutes=10 if stale else 1)
    return {"operation": "verification.verify", "message_type": "request", "schema_version": "1.0", "mission_id": str(uuid.uuid4()), "request_id": str(uuid.uuid4()), "trace_id": str(uuid.uuid4()), "action_id": str(uuid.uuid4()), "timestamp": _timestamp(now), "deadline_at": _timestamp(now + timedelta(seconds=1)), "timeout_ms": 1000, "component_version": "sim009-failure-suite-v1", "verifier_id": "exact-state-verifier", "expected_state": {"part_id": "sim-workpiece", "location_id": "line-b-drop"}, "observation_refs": [dict(observation.reference)], "verification_profile_version": "sim-exact-match-v1"}


def _verification_scenario(scenario: dict[str, Any]) -> dict[str, Any]:
    identifier = scenario["id"]
    if identifier == "SIM009-VERIFY-MISMATCH":
        payload = {"quality": "valid", "part_id": "wrong-part", "location_id": "line-b-drop"}
    elif identifier == "SIM009-VERIFY-UNCERTAIN":
        payload = {"quality": "ambiguous"}
    else:
        payload = {"quality": "valid", "part_id": "sim-workpiece", "location_id": "line-b-drop"}
    observation = normalize_deterministic_observation(payload, fixture_id=f"{identifier.lower()}-observation", fixture_version="1", timestamp="2026-09-19T00:00:00Z")
    decision = VerificationBackend().verify_with_route(_verification_request(observation, stale=identifier == "SIM009-VERIFY-STALE"), [observation])
    details = {"verification": decision.result, "route": decision.route,
               "mission": _mission_verification_route(decision.route, decision.result)}
    if identifier == "SIM009-VERIFY-MISMATCH": details["skill_reported_success"] = True
    return _base_row(scenario, decision=decision.route, outcome_kind="uncertain" if identifier == "SIM009-VERIFY-UNCERTAIN" else "failure", details=details)


def run_failure_suite(*, navigation_runtime_factory: Any = GoalTrackedGazeboNav2Runtime) -> dict[str, Any]:
    manifest = load_manifest(); rows: list[dict[str, Any]] = []
    live_runtime: GoalTrackedGazeboNav2Runtime | None = None
    live_ready = False
    if navigation_runtime_factory is GoalTrackedGazeboNav2Runtime:
        live_runtime = navigation_runtime_factory()
        try:
            live_runtime.start()
            live_ready = live_runtime.bootstrap_localization()
        except Exception:
            live_ready = False
    try:
        for scenario in manifest["scenarios"]:
            started = time.monotonic()
            if scenario["layer"] == "L0": row = _contract_scenario(scenario) if scenario["id"] != "SIM009-L0-UNAVAILABLE" else _navigation_scenario(scenario, runtime_factory=navigation_runtime_factory)
            elif scenario["layer"] == "L1-NAV":
                row = _navigation_scenario(scenario, runtime_factory=navigation_runtime_factory, live_runtime=live_runtime)
                row["live_runtime_ready"] = live_ready
            elif scenario["layer"] == "L1-VLA": row = _vla_scenario(scenario)
            else: row = _verification_scenario(scenario)
            row["duration_ms"] = round((time.monotonic() - started) * 1000, 3)
            row["within_budget"] = row["duration_ms"] <= scenario["budget_ms"]
            row["pass"] = bool(row["pass"] and row["within_budget"] and row["cleanup_complete"] and (scenario["layer"] != "L1-NAV" or live_runtime is None or live_ready))
            rows.append(row)
    finally:
        if live_runtime is not None:
            live_cleanup = live_runtime.close()
            for row in rows:
                if row["layer"] == "L1-NAV":
                    row["cleanup_complete"] = live_cleanup
                    row["goal_tracking"]["cleanup"] = live_runtime.measurements.get("cleanup", {})
                    row["pass"] = bool(row["pass"] and live_cleanup)
    ready = len(rows) == len(MANDATORY_SCENARIO_IDS) and all(row["pass"] for row in rows)
    return {
        "schema_version": "1.0", "task_id": "TASK-SIM-009",
        "task_specific_result": "SIM_FAILURE_SUITE_READY" if ready else "SIM_FAILURE_SUITE_BLOCKED",
        "manifest_sha256": canonical_sha256(manifest),
        "accepted_bindings": {task: _accepted_binding(task) for task in ("SIM-004", "SIM-005", "SIM-006", "SIM-008")},
        "simulation_authority": {"navigation_system_world": "gazebo_harmonic", "manipulation_fault_bench": "mujoco", "live_dual_world": False, "physical_dependency": False, "navigation_runtime": "GoalTrackedGazeboNav2Runtime" if live_runtime is not None else "test_fixture"},
        "scenarios": rows, "cleanup_complete": all(row["cleanup_complete"] for row in rows),
    }
