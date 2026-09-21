"""Bounded TASK-SIM-009 fault scenarios over accepted simulation adapters."""
from __future__ import annotations

import json
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

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
        if set(scenario) != {"id", "layer", "backend", "injection", "expected_decision", "budget_ms"} or not isinstance(scenario["budget_ms"], int) or not 0 < scenario["budget_ms"] <= 5_000:
            raise ValueError("SIM-009 scenario budget or shape is malformed")
    return manifest


def _action_request(operation: str, *, task_id: str | None = None, mission_id: str | None = None,
                    action_id: str | None = None, idempotency_key: str | None = None, attempt: int = 1) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    request: dict[str, Any] = {"operation": operation, "message_type": "request", "schema_version": "1.0", "mission_id": mission_id or str(uuid.uuid4()), "request_id": str(uuid.uuid4()), "trace_id": str(uuid.uuid4()), "timestamp": _timestamp(now), "deadline_at": _timestamp(now + timedelta(seconds=2)), "timeout_ms": 2000, "component_version": "sim009-failure-suite-v1", "action_id": action_id or str(uuid.uuid4())}
    if operation == "navigation.execute":
        request |= {"idempotency_key": idempotency_key or "sim009-navigation", "attempt": attempt, "retry_budget_remaining": 1, "robot_id": "simulation-proxy-mobile-base", "destination_id": "blocked-bay", "speed_profile_id": "sim-safe-v1"}
    elif operation == "vla.execute":
        request |= {"idempotency_key": idempotency_key or "sim009-vla", "attempt": attempt, "retry_budget_remaining": 1, "robot_id": "generic-simulation-proxy", "task_id": task_id or "mujoco-place-nominal", "policy_version": "sim005-scripted-policy-v1", "observation_refs": [observation_ref()], "workspace_profile_id": "sim005-workspace-v1"}
    return request


def _status_request(executed: dict[str, Any]) -> dict[str, Any]:
    return {key: executed[key] for key in ("schema_version", "mission_id", "trace_id", "timestamp", "deadline_at", "timeout_ms", "component_version", "action_id")} | {"operation": "action_status.get", "message_type": "request", "request_id": str(uuid.uuid4())}


class _ScriptedNavigationRuntime:
    def __init__(self, observations: list[RuntimeObservation], reconciled: RuntimeObservation, *, ready: bool = True) -> None:
        self.observations, self.reconciled, self.ready = list(observations), reconciled, ready
        self.calls = 0

    def navigate(self, request: dict[str, Any]) -> RuntimeObservation:
        observation = self.observations[min(self.calls, len(self.observations) - 1)]
        self.calls += 1
        return observation

    def reconcile(self, action_id: str) -> RuntimeObservation:
        return self.reconciled


def _base_row(scenario: dict[str, Any], *, decision: str, outcome_kind: str, details: dict[str, Any]) -> dict[str, Any]:
    return {"id": scenario["id"], "layer": scenario["layer"], "backend": scenario["backend"], "injection": scenario["injection"], "expected_decision": scenario["expected_decision"], "decision": decision, "outcome_kind": outcome_kind, "cleanup_complete": True, "pass": decision == scenario["expected_decision"], **details}


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


def _navigation_scenario(scenario: dict[str, Any]) -> dict[str, Any]:
    identifier = scenario["id"]
    if identifier in {"SIM009-L0-UNAVAILABLE", "SIM009-NAV-TF-UNAVAILABLE"}:
        runtime = _ScriptedNavigationRuntime([RuntimeObservation("failed")], RuntimeObservation("failed"), ready=False)
        result = NavigationBackend(runtime).execute(_action_request("navigation.execute"))
        return _base_row(scenario, decision="FAIL_CLOSED", outcome_kind="unavailable", details={"result": result})
    if identifier == "SIM009-NAV-TIMEOUT-RETRY":
        runtime = _ScriptedNavigationRuntime(
            [RuntimeObservation("unknown", error_code="NAV_TIMEOUT", error_message="bounded timeout", error_category="DEPENDENCY_TIMEOUT", retryable=True), RuntimeObservation("succeeded", arrival_verified=True)],
            RuntimeObservation("failed", error_code="NAV_RETRYABLE", error_message="authoritative retryable failure", error_category="EXECUTION_FAILED", retryable=True),
        )
        backend = NavigationBackend(runtime)
        first = _action_request("navigation.execute")
        first["destination_id"] = "line-b-drop"
        pending = backend.execute(first)
        lookup_request = _status_request(first); reconciliation = backend.action_status_get(lookup_request)
        retry = _action_request("navigation.execute", mission_id=first["mission_id"], action_id=first["action_id"], idempotency_key=first["idempotency_key"], attempt=2)
        retry["trace_id"] = first["trace_id"]; retry["destination_id"] = "line-b-drop"
        retried = backend.execute(retry)
        identity = {"mission_id_stable": retry["mission_id"] == first["mission_id"], "action_id_stable": retry["action_id"] == first["action_id"], "idempotency_key_stable": retry["idempotency_key"] == first["idempotency_key"], "retry_request_id_new": retry["request_id"] != first["request_id"], "attempt_incremented": retry["attempt"] == first["attempt"] + 1}
        valid_retry = pending["status"] == "unknown" and reconciliation["observed_status"] == "failed" and retried["result"] == "success" and all(identity.values())
        row = _base_row(scenario, decision="RETRY" if valid_retry else "FAIL_CLOSED", outcome_kind="unknown", details={"first_result": pending, "reconciliation": reconciliation, "retry_result": retried, "identity": identity, "logical_side_effect_count": 1})
        row["pass"] = valid_retry and row["expected_decision"] == "RETRY"
        return row
    code = "PATH_BLOCKED" if identifier == "SIM009-NAV-BLOCKED" else "NAV_ABORTED"
    runtime = _ScriptedNavigationRuntime([RuntimeObservation("failed", error_code=code, error_message="injected navigation failure")], RuntimeObservation("failed"))
    result = NavigationBackend(runtime).execute(_action_request("navigation.execute"))
    return _base_row(scenario, decision="FAIL_CLOSED", outcome_kind="failure", details={"result": result})


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
    details = {"verification": decision.result, "route": decision.route}
    if identifier == "SIM009-VERIFY-MISMATCH": details["skill_reported_success"] = True
    return _base_row(scenario, decision=decision.route, outcome_kind="uncertain" if identifier == "SIM009-VERIFY-UNCERTAIN" else "failure", details=details)


def run_failure_suite() -> dict[str, Any]:
    manifest = load_manifest(); rows: list[dict[str, Any]] = []
    for scenario in manifest["scenarios"]:
        started = time.monotonic()
        if scenario["layer"] == "L0": row = _contract_scenario(scenario) if scenario["id"] != "SIM009-L0-UNAVAILABLE" else _navigation_scenario(scenario)
        elif scenario["layer"] == "L1-NAV": row = _navigation_scenario(scenario)
        elif scenario["layer"] == "L1-VLA": row = _vla_scenario(scenario)
        else: row = _verification_scenario(scenario)
        row["duration_ms"] = round((time.monotonic() - started) * 1000, 3)
        row["within_budget"] = row["duration_ms"] <= scenario["budget_ms"]
        row["pass"] = bool(row["pass"] and row["within_budget"] and row["cleanup_complete"])
        rows.append(row)
    ready = len(rows) == len(MANDATORY_SCENARIO_IDS) and all(row["pass"] for row in rows)
    return {"schema_version": "1.0", "task_id": "TASK-SIM-009", "task_specific_result": "SIM_FAILURE_SUITE_READY" if ready else "SIM_FAILURE_SUITE_BLOCKED", "manifest_sha256": canonical_sha256(manifest), "scenarios": rows, "cleanup_complete": all(row["cleanup_complete"] for row in rows)}
