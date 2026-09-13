"""Minimal deterministic smoke proof for the accepted Simulation Lane contract."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker


ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = ROOT / "docs/contracts/schemas/simulation_execution_contract_v1.schema.json"
SCHEMA = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
FORMAT_CHECKER = FormatChecker()

MISSION_ID = "0d47cf1c-31c9-4f80-a8ac-6bd1a8726194"
TRACE_ID = "e97dc5ad-095a-4690-954b-f8afac14490a"
TIMESTAMP = "2026-09-13T00:00:00Z"
DEADLINE = "2026-09-13T00:00:01Z"
COMPONENT_VERSION = "sim-smoke-runtime-v1"
FIXTURE_SET_ID = "SIM_FIXTURE_SET_V1"
EXECUTION_BOUND_MS = 1_000


class ContractViolation(ValueError):
    """Raised when a smoke fixture or message violates accepted contract semantics."""


@FORMAT_CHECKER.checks("date-time", raises=(TypeError, ValueError))
def _is_calendar_valid_utc_timestamp(value: object) -> bool:
    if not isinstance(value, str):
        return True
    if not value.endswith("Z"):
        return False
    parsed = datetime.fromisoformat(f"{value[:-1]}+00:00")
    return parsed.utcoffset() is not None and parsed.utcoffset().total_seconds() == 0


VALIDATOR = Draft202012Validator(SCHEMA, format_checker=FORMAT_CHECKER)


def canonical_sha256(value: object) -> str:
    """Hash a JSON-compatible value using the accepted canonical representation."""
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return hashlib.sha256(payload).hexdigest()


def validate_contract_message(message: object) -> None:
    """Validate structural and request-time semantics, failing closed on ambiguity."""
    errors = sorted(VALIDATOR.iter_errors(message), key=lambda error: tuple(str(part) for part in error.path))
    if errors:
        raise ContractViolation("; ".join(error.message for error in errors))
    if isinstance(message, dict) and message.get("message_type") == "request":
        timestamp = datetime.fromisoformat(str(message["timestamp"]).replace("Z", "+00:00"))
        deadline = datetime.fromisoformat(str(message["deadline_at"]).replace("Z", "+00:00"))
        if deadline <= timestamp:
            raise ContractViolation("deadline_at must be later than timestamp")


def _common_request(operation: str, request_id: str) -> dict[str, Any]:
    return {
        "operation": operation,
        "message_type": "request",
        "schema_version": "1.0",
        "mission_id": MISSION_ID,
        "request_id": request_id,
        "trace_id": TRACE_ID,
        "timestamp": TIMESTAMP,
        "deadline_at": DEADLINE,
        "timeout_ms": EXECUTION_BOUND_MS,
        "component_version": COMPONENT_VERSION,
    }


def _common_result(operation: str, request_id: str) -> dict[str, Any]:
    return {
        "operation": operation,
        "message_type": "result",
        "schema_version": "1.0",
        "mission_id": MISSION_ID,
        "request_id": request_id,
        "trace_id": TRACE_ID,
        "timestamp": TIMESTAMP,
        "component_version": COMPONENT_VERSION,
        "source_kind": "mock",
    }


def _error(category: str, *, retryable: bool = False) -> dict[str, Any]:
    return {
        "code": f"SIM_{category}",
        "message": "deterministic simulation fixture result",
        "category": category,
        "retryable": retryable,
    }


def _evidence_ref(uri_suffix: str) -> dict[str, str]:
    return {
        "uri": f"urn:factory-evidence:sim-002:{uri_suffix}",
        "sha256": hashlib.sha256(uri_suffix.encode()).hexdigest(),
    }


def _manifest(quality: str = "valid") -> dict[str, Any]:
    observation: dict[str, str] = {"quality": quality}
    if quality == "valid":
        observation.update({"part_id": "brake-ecu-b", "location_id": "line-b"})
    return {
        "schema_version": "1.0",
        "fixture_set_id": FIXTURE_SET_ID,
        "fixture_set_version": "1",
        "source_kind": "mock",
        "fixtures": [
            {
                "fixture_id": f"observation-{quality}",
                "fixture_version": "1",
                "content_sha256": canonical_sha256(observation),
                "timestamp": TIMESTAMP,
                "source_kind": "mock",
                "observation": observation,
            }
        ],
    }


def _observation_ref(manifest: dict[str, Any]) -> dict[str, str]:
    fixture = manifest["fixtures"][0]
    return {
        "fixture_set_id": manifest["fixture_set_id"],
        "fixture_id": fixture["fixture_id"],
        "fixture_version": fixture["fixture_version"],
        "content_sha256": fixture["content_sha256"],
        "timestamp": fixture["timestamp"],
        "source_kind": fixture["source_kind"],
    }


def _validated_fixture(request: dict[str, Any], manifest: dict[str, Any]) -> dict[str, str]:
    validate_contract_message(manifest)
    reference = request["observation_refs"][0]
    if reference["fixture_set_id"] != manifest["fixture_set_id"]:
        raise ContractViolation("observation fixture_set_id mismatch")
    matches = [
        fixture
        for fixture in manifest["fixtures"]
        if fixture["fixture_id"] == reference["fixture_id"]
        and fixture["fixture_version"] == reference["fixture_version"]
    ]
    if len(matches) != 1:
        raise ContractViolation("observation reference must resolve exactly once")
    fixture = matches[0]
    for field in ("content_sha256", "timestamp", "source_kind"):
        if fixture[field] != reference[field]:
            raise ContractViolation(f"observation reference {field} mismatch")
    if canonical_sha256(fixture["observation"]) != fixture["content_sha256"]:
        raise ContractViolation("fixture content hash mismatch")
    return fixture["observation"]


def _deterministic_verdict(request: dict[str, Any], manifest: dict[str, Any]) -> str:
    observation = _validated_fixture(request, manifest)
    if observation["quality"] != "valid":
        return "uncertain"
    expected = request["expected_state"]
    return (
        "pass"
        if observation["part_id"] == expected["part_id"]
        and observation["location_id"] == expected["location_id"]
        else "fail"
    )


def _validate_pair(request: dict[str, Any], result: dict[str, Any], *, action_bound: bool) -> None:
    validate_contract_message(request)
    validate_contract_message(result)
    for field in ("operation", "mission_id", "request_id", "trace_id"):
        if request[field] != result[field]:
            raise ContractViolation(f"{field} mismatch")
    if action_bound and request["action_id"] != result["action_id"]:
        raise ContractViolation("action_id mismatch")
    if request["operation"] == "navigation.execute" and result["result"] == "success":
        if result["arrival"]["destination_id"] != request["destination_id"]:
            raise ContractViolation("navigation destination_id mismatch")


def _validate_reconciliation(
    status_request: dict[str, Any],
    status_result: dict[str, Any],
    reconciliation: dict[str, Any],
) -> None:
    _validate_pair(status_request, status_result, action_bound=True)
    validate_contract_message(reconciliation)
    if status_result["result"] != "success":
        raise ContractViolation("status lookup did not return authoritative evidence")
    relationships = {
        "mission_id": status_request["mission_id"],
        "action_id": status_request["action_id"],
        "status_request_id": status_request["request_id"],
        "status_result_request_id": status_result["request_id"],
        "resolved_status": status_result["observed_status"],
        "observed_at": status_result["observed_at"],
        "component_version": status_result["component_version"],
        "evidence_refs": status_result["evidence_refs"],
    }
    for field, expected in relationships.items():
        if reconciliation[field] != expected:
            raise ContractViolation(f"reconciliation {field} mismatch")


def _navigation_request(request_id: str, action_id: str) -> dict[str, Any]:
    request = _common_request("navigation.execute", request_id)
    request.update(
        {
            "robot_id": "amr-sim-001",
            "idempotency_key": f"navigation-{action_id}",
            "action_id": action_id,
            "attempt": 1,
            "retry_budget_remaining": 1,
            "destination_id": "line-b-drop",
            "speed_profile_id": "sim-safe-v1",
        }
    )
    return request


def _vla_request(request_id: str, action_id: str, manifest: dict[str, Any]) -> dict[str, Any]:
    request = _common_request("vla.execute", request_id)
    request.update(
        {
            "robot_id": "manipulator-sim-001",
            "idempotency_key": f"vla-{action_id}",
            "action_id": action_id,
            "attempt": 1,
            "retry_budget_remaining": 1,
            "task_id": "place-brake-ecu",
            "policy_version": "fixture-policy-v1",
            "observation_refs": [_observation_ref(manifest)],
            "workspace_profile_id": "sim-workspace-v1",
        }
    )
    return request


def _verification_request(request_id: str, action_id: str, manifest: dict[str, Any]) -> dict[str, Any]:
    request = _common_request("verification.verify", request_id)
    request.update(
        {
            "action_id": action_id,
            "verifier_id": "exact-state-verifier",
            "expected_state": {"part_id": "brake-ecu-b", "location_id": "line-b"},
            "observation_refs": [_observation_ref(manifest)],
            "verification_profile_version": "sim-exact-match-v1",
        }
    )
    return request


def _success_scenario() -> dict[str, Any]:
    manifest = _manifest()
    navigation_request = _navigation_request(
        "dc0699c5-a2a8-4a15-b5e4-f6358f0c2688",
        "35ae5d55-ca49-4962-ba84-2d0093e46f7f",
    )
    navigation_result = _common_result("navigation.execute", navigation_request["request_id"])
    navigation_result.update(
        {
            "action_id": navigation_request["action_id"],
            "status": "succeeded",
            "result": "success",
            "arrival": {"destination_id": navigation_request["destination_id"], "verified": True},
            "evidence_refs": [_evidence_ref("navigation-success")],
        }
    )
    _validate_pair(navigation_request, navigation_result, action_bound=True)

    vla_request = _vla_request(
        "a1f24c6d-b465-48aa-94ed-250584a40b42",
        "4fa19c98-54ab-4b2f-8338-5012f99a97ba",
        manifest,
    )
    vla_result = _common_result("vla.execute", vla_request["request_id"])
    vla_result.update(
        {
            "action_id": vla_request["action_id"],
            "status": "succeeded",
            "result": "success",
            "skill_outcome": "succeeded",
            "verifier_input_refs": [_evidence_ref("vla-success")],
            "latency_ms": 5,
            "evidence_refs": [_evidence_ref("vla-result")],
        }
    )
    _validate_pair(vla_request, vla_result, action_bound=True)

    verification_request = _verification_request(
        "bd0eec59-39ee-4ee1-ab1e-fea8cfd4b636",
        vla_request["action_id"],
        manifest,
    )
    verdict = _deterministic_verdict(verification_request, manifest)
    verification_result = _common_result("verification.verify", verification_request["request_id"])
    verification_result.update(
        {
            "action_id": verification_request["action_id"],
            "status": "succeeded",
            "result": "success",
            "verification_profile_version": "sim-exact-match-v1",
            "verdict": verdict,
            "confidence": 1.0,
            "evidence_refs": [_evidence_ref("verification-pass")],
        }
    )
    _validate_pair(verification_request, verification_result, action_bound=True)
    if verdict != "pass":
        raise ContractViolation("successful smoke mission requires verification pass")

    mission_request = _common_request("mission.execute", "7e45804f-c5a1-4930-bb49-ac1627b02025")
    mission_request.update(
        {
            "idempotency_key": "mission-line-b-001",
            "goal": {
                "mission_type": "line_side_supply",
                "priority": 50,
                "line_id": "line-b",
                "part_id": "brake-ecu-b",
                "quantity": 1,
                "source_id": "warehouse-a",
                "destination_id": "line-b-drop",
                "approval_context": {
                    "simulation_only": True,
                    "approved": True,
                    "authorized_by": "TASK-SIM-001-acceptance",
                },
            },
        }
    )
    mission_result = _common_result("mission.execute", mission_request["request_id"])
    mission_result.update(
        {"status": "completed", "result": "success", "checkpoint_revision": 4, "outcome": "completed"}
    )
    _validate_pair(mission_request, mission_result, action_bound=False)
    return {
        "scenario_id": "S01",
        "name": "deterministic_success",
        "status": "PASS",
        "operations": ["mission.execute", "navigation.execute", "vla.execute", "verification.verify"],
        "final_mission_status": "completed",
        "verification_verdict": verdict,
        "contract_messages_validated": 8,
        "execution_bound_ms": EXECUTION_BOUND_MS,
    }


def _failure_scenario() -> dict[str, Any]:
    request = _navigation_request(
        "ee0d7a04-b660-48c1-8b64-b6a017e10009",
        "6fded914-0c29-4977-a03e-975a84ee8e16",
    )
    result = _common_result("navigation.execute", request["request_id"])
    result.update(
        {
            "action_id": request["action_id"],
            "status": "failed",
            "result": "failure",
            "error": _error("EXECUTION_FAILED"),
        }
    )
    _validate_pair(request, result, action_bound=True)
    return {
        "scenario_id": "S02",
        "name": "deterministic_failure",
        "status": "PASS",
        "operation": "navigation.execute",
        "observed_status": result["status"],
        "observed_result": result["result"],
        "error_category": result["error"]["category"],
        "execution_bound_ms": EXECUTION_BOUND_MS,
    }


def _timeout_scenario() -> dict[str, Any]:
    manifest = _manifest()
    request = _vla_request(
        "73a9e4ee-cb9e-4985-b5e1-32a706e74d75",
        "8a47857b-6084-464d-aacc-a8ee8c1999ce",
        manifest,
    )
    result = _common_result("vla.execute", request["request_id"])
    result.update(
        {
            "action_id": request["action_id"],
            "status": "unknown",
            "result": "pending",
            "skill_outcome": "uncertain",
            "latency_ms": EXECUTION_BOUND_MS,
            "error": _error("MODEL_TIMEOUT"),
        }
    )
    _validate_pair(request, result, action_bound=True)
    transition = {"record_type": "action_transition", "from_status": "running", "to_status": "unknown"}
    validate_contract_message(transition)
    return {
        "scenario_id": "S03",
        "name": "bounded_timeout",
        "status": "PASS",
        "operation": "vla.execute",
        "observed_status": result["status"],
        "observed_result": result["result"],
        "error_category": result["error"]["category"],
        "virtual_no_result_at_bound": True,
        "execution_bound_ms": EXECUTION_BOUND_MS,
    }


def _reconciliation_scenario() -> dict[str, Any]:
    request = _navigation_request(
        "d18e3279-82a6-4cd4-a1d3-30a7df2df367",
        "7824bc81-00bb-4c38-ae55-81a6e0148223",
    )
    timeout_result = _common_result("navigation.execute", request["request_id"])
    timeout_result.update(
        {
            "action_id": request["action_id"],
            "status": "unknown",
            "result": "pending",
            "error": _error("DEPENDENCY_TIMEOUT"),
        }
    )
    _validate_pair(request, timeout_result, action_bound=True)
    status_request = _common_request("action_status.get", "cc9cbdf8-d734-4ead-b152-3bf75f58ade8")
    status_request["action_id"] = request["action_id"]
    status_result = _common_result("action_status.get", status_request["request_id"])
    status_result.update(
        {
            "action_id": request["action_id"],
            "status": "succeeded",
            "result": "success",
            "observed_at": TIMESTAMP,
            "observed_status": "succeeded",
            "evidence_refs": [_evidence_ref("reconciliation-succeeded")],
        }
    )
    reconciliation = {
        "record_type": "reconciliation_record",
        "schema_version": "1.0",
        "mission_id": MISSION_ID,
        "action_id": request["action_id"],
        "status_request_id": status_request["request_id"],
        "status_result_request_id": status_result["request_id"],
        "from_status": "unknown",
        "phase": "reconciling",
        "status": "reconciled",
        "resolved_status": status_result["observed_status"],
        "observed_at": status_result["observed_at"],
        "component_version": COMPONENT_VERSION,
        "evidence_refs": status_result["evidence_refs"],
    }
    _validate_reconciliation(status_request, status_result, reconciliation)
    transitions = [
        {"record_type": "action_transition", "from_status": "unknown", "to_status": "reconciling"},
        {
            "record_type": "action_transition",
            "from_status": "reconciling",
            "to_status": "reconciled",
            "resolved_status": "succeeded",
            "reconciliation_evidence": status_result["evidence_refs"][0],
        },
    ]
    for transition in transitions:
        validate_contract_message(transition)
    return {
        "scenario_id": "S04",
        "name": "unknown_then_authoritative_reconciliation",
        "status": "PASS",
        "operation": "action_status.get",
        "initial_status": "unknown",
        "state_sequence": ["unknown", "reconciling", "reconciled"],
        "resolved_status": reconciliation["resolved_status"],
        "direct_unknown_to_succeeded": False,
        "authoritative_evidence_required": True,
        "execution_bound_ms": EXECUTION_BOUND_MS,
    }


def run_smoke_suite() -> dict[str, Any]:
    """Execute the four bounded deterministic scenarios without external side effects."""
    scenarios = [
        _success_scenario(),
        _failure_scenario(),
        _timeout_scenario(),
        _reconciliation_scenario(),
    ]
    if any(scenario["status"] != "PASS" for scenario in scenarios):
        raise ContractViolation("all mandatory smoke scenarios must pass")
    return {
        "schema_version": "1.0",
        "runtime_version": COMPONENT_VERSION,
        "fixture_set_id": FIXTURE_SET_ID,
        "scenarios": scenarios,
        "boundedness": {
            "all_scenarios_bounded": True,
            "maximum_execution_bound_ms": EXECUTION_BOUND_MS,
            "sleep_used": False,
            "retries_performed": 0,
        },
        "process_cleanup": {
            "child_processes_started": 0,
            "background_workers_started": 0,
            "temporary_files_created": 0,
            "cleanup_complete": True,
        },
        "isolation": {
            "physical_dependency": False,
            "physical_motion_executed": False,
            "physical_camera_dependency": False,
            "physical_teleop_dependency": False,
            "network_dependency": False,
            "training_dependency": False,
            "dataset_v1_created": False,
            "week_authorization_modified": False,
        },
    }
