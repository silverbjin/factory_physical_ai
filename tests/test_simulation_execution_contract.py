from __future__ import annotations

import copy
import hashlib
import json
import unittest
from datetime import datetime
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "docs/contracts/schemas/simulation_execution_contract_v1.schema.json"
SCHEMA = json.loads(SCHEMA_PATH.read_text())
VALIDATOR = Draft202012Validator(SCHEMA, format_checker=FormatChecker())

MISSION_ID = "0d47cf1c-31c9-4f80-a8ac-6bd1a8726194"
ACTION_ID = "35ae5d55-ca49-4962-ba84-2d0093e46f7f"
REQUEST_ID = "dc0699c5-a2a8-4a15-b5e4-f6358f0c2688"
STATUS_REQUEST_ID = "2450bf05-b44b-4f7f-9f13-a25963997ff7"
RETRY_REQUEST_ID = "a1f24c6d-b465-48aa-94ed-250584a40b42"
TRACE_ID = "e97dc5ad-095a-4690-954b-f8afac14490a"
TIMESTAMP = "2026-09-12T00:00:00Z"
DEADLINE = "2026-09-12T00:00:30Z"
SHA = "a" * 64


class ContractSemanticError(ValueError):
    """Raised by test-only predicates when normative cross-message rules fail."""


def _canonical_sha256(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return hashlib.sha256(payload).hexdigest()


def _error(*, retryable: bool = False, category: str = "EXECUTION_FAILED") -> dict[str, object]:
    return {
        "code": "SIM_FAILURE",
        "message": "deterministic contract failure",
        "category": category,
        "retryable": retryable,
    }


def _evidence_ref() -> dict[str, str]:
    return {"uri": "urn:factory-evidence:sim-c01", "sha256": SHA}


def _common_request(operation: str, *, request_id: str = REQUEST_ID) -> dict[str, object]:
    return {
        "operation": operation,
        "message_type": "request",
        "schema_version": "1.0",
        "mission_id": MISSION_ID,
        "request_id": request_id,
        "trace_id": TRACE_ID,
        "timestamp": TIMESTAMP,
        "deadline_at": DEADLINE,
        "timeout_ms": 30000,
        "component_version": "sim-contract-test-1",
    }


def _common_result(operation: str, *, request_id: str = REQUEST_ID) -> dict[str, object]:
    return {
        "operation": operation,
        "message_type": "result",
        "schema_version": "1.0",
        "mission_id": MISSION_ID,
        "request_id": request_id,
        "trace_id": TRACE_ID,
        "timestamp": TIMESTAMP,
        "component_version": "sim-contract-test-1",
        "source_kind": "mock",
    }


def _observation(quality: str = "valid", *, part_id: str = "brake-ecu-b", location_id: str = "line-b") -> dict[str, str]:
    if quality == "valid":
        return {"quality": quality, "part_id": part_id, "location_id": location_id}
    return {"quality": quality}


def _observation_ref(observation: dict[str, str] | None = None) -> dict[str, str]:
    content = observation or _observation()
    return {
        "fixture_set_id": "SIM_FIXTURE_SET_V1",
        "fixture_id": "obs-001",
        "fixture_version": "1",
        "content_sha256": _canonical_sha256(content),
        "timestamp": TIMESTAMP,
        "source_kind": "mock",
    }


def _manifest(observation: dict[str, str] | None = None) -> dict[str, object]:
    content = observation or _observation()
    reference = _observation_ref(content)
    return {
        "schema_version": "1.0",
        "fixture_set_id": "SIM_FIXTURE_SET_V1",
        "fixture_set_version": "1",
        "source_kind": "mock",
        "fixtures": [
            {
                "fixture_id": reference["fixture_id"],
                "fixture_version": reference["fixture_version"],
                "content_sha256": reference["content_sha256"],
                "timestamp": reference["timestamp"],
                "source_kind": "mock",
                "observation": content,
            }
        ],
    }


def _mission_request() -> dict[str, object]:
    request = _common_request("mission.execute")
    request.update(
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
                    "authorized_by": "simulation-contract-test",
                },
            },
        }
    )
    return request


def _mission_result() -> dict[str, object]:
    result = _common_result("mission.execute")
    result.update({"status": "completed", "result": "success", "checkpoint_revision": 4, "outcome": "completed"})
    return result


def _navigation_request(*, request_id: str = REQUEST_ID, attempt: int = 1, budget: int = 1) -> dict[str, object]:
    request = _common_request("navigation.execute", request_id=request_id)
    request.update(
        {
            "idempotency_key": "navigation-line-b-001",
            "action_id": ACTION_ID,
            "attempt": attempt,
            "retry_budget_remaining": budget,
            "robot_id": "amr-sim-001",
            "destination_id": "line-b-drop",
            "speed_profile_id": "sim-safe-v1",
        }
    )
    return request


def _navigation_result() -> dict[str, object]:
    result = _common_result("navigation.execute")
    result.update(
        {
            "action_id": ACTION_ID,
            "status": "succeeded",
            "result": "success",
            "arrival": {"destination_id": "line-b-drop", "verified": True},
            "evidence_refs": [_evidence_ref()],
        }
    )
    return result


def _vla_request() -> dict[str, object]:
    request = _common_request("vla.execute")
    request.update(
        {
            "idempotency_key": "vla-place-001",
            "action_id": ACTION_ID,
            "attempt": 1,
            "retry_budget_remaining": 1,
            "robot_id": "manipulator-sim-001",
            "task_id": "place-brake-ecu",
            "policy_version": "fixture-policy-v1",
            "observation_refs": [_observation_ref()],
            "workspace_profile_id": "sim-workspace-v1",
        }
    )
    return request


def _vla_result() -> dict[str, object]:
    result = _common_result("vla.execute")
    result.update(
        {
            "action_id": ACTION_ID,
            "status": "succeeded",
            "result": "success",
            "skill_outcome": "succeeded",
            "verifier_input_refs": [_evidence_ref()],
            "latency_ms": 5,
            "evidence_refs": [_evidence_ref()],
        }
    )
    return result


def _status_request() -> dict[str, object]:
    request = _common_request("action_status.get", request_id=STATUS_REQUEST_ID)
    request["action_id"] = ACTION_ID
    return request


def _status_result() -> dict[str, object]:
    result = _common_result("action_status.get", request_id=STATUS_REQUEST_ID)
    result.update(
        {
            "action_id": ACTION_ID,
            "status": "succeeded",
            "result": "success",
            "observed_at": TIMESTAMP,
            "observed_status": "failed",
            "evidence_refs": [_evidence_ref()],
        }
    )
    return result


def _verification_request(observation: dict[str, str] | None = None) -> dict[str, object]:
    request = _common_request("verification.verify")
    request.update(
        {
            "action_id": ACTION_ID,
            "verifier_id": "exact-state-verifier",
            "expected_state": {"part_id": "brake-ecu-b", "location_id": "line-b"},
            "observation_refs": [_observation_ref(observation)],
            "verification_profile_version": "sim-exact-match-v1",
        }
    )
    return request


def _verification_result(verdict: str = "pass") -> dict[str, object]:
    result = _common_result("verification.verify")
    result.update(
        {
            "action_id": ACTION_ID,
            "status": "succeeded",
            "result": "success",
            "verification_profile_version": "sim-exact-match-v1",
            "verdict": verdict,
            "confidence": 1.0 if verdict != "uncertain" else 0.0,
            "evidence_refs": [_evidence_ref()],
        }
    )
    if verdict != "pass":
        result["mismatch_code"] = "STATE_MISMATCH" if verdict == "fail" else "INSUFFICIENT_OBSERVATION"
    return result


def _assert_correlated(request: dict[str, object], result: dict[str, object], *, action_bound: bool) -> None:
    for field in ("operation", "mission_id", "request_id", "trace_id"):
        if request[field] != result[field]:
            raise ContractSemanticError(f"{field} mismatch")
    if action_bound and request["action_id"] != result["action_id"]:
        raise ContractSemanticError("action_id mismatch")


def _assert_deadline_after_timestamp(request: dict[str, object]) -> None:
    timestamp = datetime.fromisoformat(str(request["timestamp"]).replace("Z", "+00:00"))
    deadline = datetime.fromisoformat(str(request["deadline_at"]).replace("Z", "+00:00"))
    if deadline <= timestamp:
        raise ContractSemanticError("deadline_at must be later than timestamp")


def _reconciliation_record() -> dict[str, object]:
    return {
        "record_type": "reconciliation_record",
        "schema_version": "1.0",
        "mission_id": MISSION_ID,
        "action_id": ACTION_ID,
        "status_request_id": STATUS_REQUEST_ID,
        "status_result_request_id": STATUS_REQUEST_ID,
        "from_status": "unknown",
        "phase": "reconciling",
        "status": "reconciled",
        "resolved_status": "failed",
        "observed_at": TIMESTAMP,
        "component_version": "sim-contract-test-1",
        "evidence_refs": [_evidence_ref()],
        "error": _error(retryable=True),
    }


def _assert_reconciliation_matches(
    request: dict[str, object], result: dict[str, object], record: dict[str, object]
) -> None:
    _assert_correlated(request, result, action_bound=True)
    if result.get("result") != "success":
        raise ContractSemanticError("status lookup did not produce authoritative evidence")
    if record["mission_id"] != request["mission_id"] or record["action_id"] != request["action_id"]:
        raise ContractSemanticError("reconciliation identity mismatch")
    if record["status_request_id"] != request["request_id"]:
        raise ContractSemanticError("reconciliation status request mismatch")
    if record["status_result_request_id"] != result["request_id"]:
        raise ContractSemanticError("reconciliation status result mismatch")
    if record["resolved_status"] != result["observed_status"]:
        raise ContractSemanticError("reconciliation observed status mismatch")


def _retry_authorization() -> dict[str, object]:
    return {
        "record_type": "retry_authorization",
        "mission_id": MISSION_ID,
        "action_id": ACTION_ID,
        "idempotency_key": "navigation-line-b-001",
        "previous_request_id": REQUEST_ID,
        "new_request_id": RETRY_REQUEST_ID,
        "previous_attempt": 1,
        "next_attempt": 2,
        "retry_budget_remaining": 1,
        "reconciliation_completed": True,
        "resolved_status": "failed",
        "error": _error(retryable=True),
    }


def _assert_retry_semantics(
    previous: dict[str, object], new: dict[str, object], authorization: dict[str, object]
) -> None:
    if authorization["reconciliation_completed"] is not True or authorization["resolved_status"] != "failed":
        raise ContractSemanticError("retry requires reconciled failure")
    if authorization["error"]["retryable"] is not True or authorization["retry_budget_remaining"] <= 0:  # type: ignore[index,operator]
        raise ContractSemanticError("retry guard failed")
    for field in ("mission_id", "action_id", "idempotency_key"):
        if previous[field] != new[field] or previous[field] != authorization[field]:
            raise ContractSemanticError(f"retry {field} mismatch")
    if previous["request_id"] == new["request_id"]:
        raise ContractSemanticError("retry request_id must be new")
    if authorization["previous_request_id"] != previous["request_id"] or authorization["new_request_id"] != new["request_id"]:
        raise ContractSemanticError("retry request correlation mismatch")
    if new["attempt"] != previous["attempt"] + 1 or authorization["next_attempt"] != authorization["previous_attempt"] + 1:  # type: ignore[operator]
        raise ContractSemanticError("retry attempt must increment exactly once")
    if new["retry_budget_remaining"] != previous["retry_budget_remaining"] - 1:  # type: ignore[operator]
        raise ContractSemanticError("retry budget must decrement")


def _deterministic_verdict(
    request: dict[str, object], manifest: dict[str, object]
) -> str:
    reference = request["observation_refs"][0]  # type: ignore[index]
    fixtures = manifest["fixtures"]  # type: ignore[index]
    matches = [
        item
        for item in fixtures
        if item["fixture_id"] == reference["fixture_id"] and item["fixture_version"] == reference["fixture_version"]
    ]
    if len(matches) != 1:
        raise ContractSemanticError("observation reference is not uniquely resolved")
    fixture = matches[0]
    if fixture["content_sha256"] != reference["content_sha256"]:
        raise ContractSemanticError("observation content hash mismatch")
    observation = fixture["observation"]
    if _canonical_sha256(observation) != reference["content_sha256"]:
        raise ContractSemanticError("fixture content is not immutable")
    if observation["quality"] != "valid":
        return "uncertain"
    expected = request["expected_state"]
    return "pass" if all(observation[field] == expected[field] for field in ("part_id", "location_id")) else "fail"


class SimulationExecutionContractTests(unittest.TestCase):
    def assertValid(self, value: object) -> None:  # noqa: N802 - unittest assertion convention
        errors = list(VALIDATOR.iter_errors(value))
        self.assertEqual(errors, [], "\n".join(error.message for error in errors))

    def assertInvalid(self, value: object) -> None:  # noqa: N802 - unittest assertion convention
        self.assertTrue(list(VALIDATOR.iter_errors(value)))

    def test_schema_meta_validates_and_has_all_required_definitions(self) -> None:
        Draft202012Validator.check_schema(SCHEMA)
        required = {
            "CommonRequestEnvelope",
            "CommonResultEnvelope",
            "ContractError",
            "MissionExecuteRequest",
            "MissionExecuteResult",
            "NavigationExecuteRequest",
            "NavigationExecuteResult",
            "VLAExecuteRequest",
            "VLAExecuteResult",
            "ActionStatusGetRequest",
            "ActionStatusGetResult",
            "VerificationRequest",
            "VerificationResult",
            "SimulationObservationRef",
            "SimulationFixtureManifest",
        }
        self.assertTrue(required <= SCHEMA["$defs"].keys())

    def test_all_operation_request_and_result_vectors_validate(self) -> None:
        vectors = [
            _mission_request(),
            _mission_result(),
            _navigation_request(),
            _navigation_result(),
            _vla_request(),
            _vla_result(),
            _status_request(),
            _status_result(),
            _verification_request(),
            _verification_result("pass"),
            _verification_result("fail"),
            _verification_result("uncertain"),
        ]
        for value in vectors:
            with self.subTest(operation=value["operation"], result=value.get("result")):
                self.assertValid(value)
                if value["message_type"] == "request":
                    _assert_deadline_after_timestamp(value)

    def test_observation_reference_and_fixture_manifest_validate(self) -> None:
        self.assertValid(_observation_ref())
        self.assertValid(_manifest())
        self.assertValid(_manifest(_observation("insufficient")))
        self.assertValid(_manifest(_observation("ambiguous")))

    def test_required_fields_fail_closed(self) -> None:
        cases = [
            (_mission_request(), "mission_id"),
            (_mission_request(), "request_id"),
            (_mission_request(), "deadline_at"),
            (_navigation_request(), "action_id"),
        ]
        for value, field in cases:
            invalid = copy.deepcopy(value)
            invalid.pop(field)
            with self.subTest(field=field):
                self.assertInvalid(invalid)

    def test_versions_formats_and_unknown_values_fail_closed(self) -> None:
        cases = [
            (_mission_request(), "schema_version", "2.0"),
            (_mission_request(), "mission_id", "not-a-uuid"),
            (_mission_request(), "timestamp", "not-a-timestamp"),
            (_mission_result(), "status", "invented_state"),
            (_mission_result(), "result", "maybe"),
        ]
        for value, field, replacement in cases:
            invalid = copy.deepcopy(value)
            invalid[field] = replacement
            with self.subTest(field=field, replacement=replacement):
                self.assertInvalid(invalid)
        bad_error = _common_result("navigation.execute")
        bad_error.update({"action_id": ACTION_ID, "status": "failed", "result": "failure", "error": _error(category="UNKNOWN")})
        self.assertInvalid(bad_error)

    def test_malformed_sha_and_physical_or_dataset_fixture_alias_fail(self) -> None:
        malformed = _observation_ref()
        malformed["content_sha256"] = "not-sha256"
        self.assertInvalid(malformed)
        physical = _observation_ref()
        physical["source_kind"] = "camera"
        self.assertInvalid(physical)
        dataset_alias = _manifest()
        dataset_alias["fixture_set_id"] = "Dataset V1"
        self.assertInvalid(dataset_alias)

    def test_unknown_operation_and_unknown_public_fields_fail_closed(self) -> None:
        unknown = _mission_request()
        unknown["operation"] = "mission.run"
        self.assertInvalid(unknown)
        extra = _mission_request()
        extra["authorization_default"] = True
        self.assertInvalid(extra)

    def test_navigation_rejects_all_raw_control_fields(self) -> None:
        forbidden = (
            "raw_pose",
            "raw_path",
            "trajectory",
            "planner_parameters",
            "controller_parameters",
            "ros_command",
            "nav2_command",
            "nav2_lifecycle_command",
        )
        for field in forbidden:
            request = _navigation_request()
            request[field] = {}
            with self.subTest(field=field):
                self.assertInvalid(request)

    def test_vla_rejects_all_actuator_and_controller_fields(self) -> None:
        forbidden = (
            "joint_command",
            "motor_command",
            "gripper_command",
            "trajectory_command",
            "raw_action_chunks",
            "moveit_command",
            "ros2_control_command",
            "hardware_controller_command",
        )
        for field in forbidden:
            request = _vla_request()
            request[field] = [0.0]
            with self.subTest(field=field):
                self.assertInvalid(request)

    def test_non_success_without_error_and_false_success_fail(self) -> None:
        missing_error = _navigation_result()
        missing_error.update({"status": "unknown", "result": "pending"})
        missing_error.pop("arrival")
        missing_error.pop("evidence_refs")
        self.assertInvalid(missing_error)
        false_success = _navigation_result()
        false_success["status"] = "failed"
        self.assertInvalid(false_success)

    def test_mission_result_rejects_hitl_or_error_outside_their_outcome(self) -> None:
        success_with_error = _mission_result()
        success_with_error["error"] = _error()
        self.assertInvalid(success_with_error)
        success_with_hitl = _mission_result()
        success_with_hitl["hitl_request"] = {"reason": "not applicable", "required_action": "none"}
        self.assertInvalid(success_with_hitl)
        failure_with_hitl = _mission_result()
        failure_with_hitl.update(
            {
                "status": "failed",
                "result": "failure",
                "outcome": "failed",
                "error": _error(),
                "hitl_request": {"reason": "wrong branch", "required_action": "none"},
            }
        )
        self.assertInvalid(failure_with_hitl)

    def test_timeout_is_pending_unknown_and_never_success_or_failure(self) -> None:
        timeout = _navigation_result()
        timeout.pop("arrival")
        timeout.update(
            {
                "status": "unknown",
                "result": "pending",
                "error": _error(retryable=False, category="DEPENDENCY_TIMEOUT"),
            }
        )
        self.assertValid(timeout)
        for status, result in (("succeeded", "success"), ("failed", "failure")):
            invalid = copy.deepcopy(timeout)
            invalid.update({"status": status, "result": result})
            with self.subTest(status=status, result=result):
                self.assertInvalid(invalid)

    def test_request_result_identity_mismatch_fails_semantic_validation(self) -> None:
        request = _navigation_request()
        result = _navigation_result()
        _assert_correlated(request, result, action_bound=True)
        for field, replacement in (("mission_id", "5f4e70dc-dffc-4ef9-9308-702b041c6d13"), ("action_id", "ed3757ab-1268-4ce1-94f8-f37f30faf92d")):
            mismatched = copy.deepcopy(result)
            mismatched[field] = replacement
            with self.subTest(field=field), self.assertRaises(ContractSemanticError):
                _assert_correlated(request, mismatched, action_bound=True)

    def test_action_transition_table_accepts_only_legal_transitions(self) -> None:
        legal = SCHEMA["x-contract-semantics"]["action_transitions"]
        for from_status, to_status in legal:
            transition: dict[str, object] = {
                "record_type": "action_transition",
                "from_status": from_status,
                "to_status": to_status,
            }
            if to_status == "reconciled":
                transition.update({"resolved_status": "succeeded", "reconciliation_evidence": _evidence_ref()})
            with self.subTest(from_status=from_status, to_status=to_status):
                self.assertValid(transition)
        self.assertInvalid({"record_type": "action_transition", "from_status": "unknown", "to_status": "succeeded"})

    def test_mission_transition_table_is_finite_and_terminal_states_are_terminal(self) -> None:
        transitions = {tuple(item) for item in SCHEMA["x-contract-semantics"]["mission_transitions"]}
        expected = {
            ("created", "ready"),
            ("created", "escalated"),
            ("ready", "executing"),
            ("ready", "escalated"),
            ("executing", "completed"),
            ("executing", "reconciling"),
            ("executing", "failed"),
            ("executing", "escalated"),
            ("reconciling", "completed"),
            ("reconciling", "recovering"),
            ("reconciling", "failed"),
            ("reconciling", "escalated"),
            ("recovering", "executing"),
            ("recovering", "failed"),
            ("recovering", "escalated"),
        }
        self.assertEqual(transitions, expected)
        for source, target in transitions:
            with self.subTest(source=source, target=target):
                self.assertValid(
                    {
                        "record_type": "mission_transition",
                        "from_status": source,
                        "to_status": target,
                    }
                )
        terminal = set(SCHEMA["x-contract-semantics"]["mission_terminal_states"])
        self.assertEqual(terminal, {"completed", "failed", "escalated"})
        self.assertFalse(any(source in terminal for source, _ in transitions))
        for source in terminal:
            with self.subTest(terminal_source=source):
                self.assertInvalid(
                    {
                        "record_type": "mission_transition",
                        "from_status": source,
                        "to_status": "executing",
                    }
                )

    def test_reconciliation_requires_matching_action_status_evidence(self) -> None:
        request = _status_request()
        result = _status_result()
        record = _reconciliation_record()
        self.assertValid(record)
        _assert_reconciliation_matches(request, result, record)
        lookup_failure = _status_result()
        lookup_failure.update({"status": "failed", "result": "failure", "error": _error()})
        for field in ("observed_at", "observed_status", "evidence_refs"):
            lookup_failure.pop(field)
        self.assertValid(lookup_failure)
        for forbidden in ("observed_at", "observed_status", "evidence_refs"):
            invalid = copy.deepcopy(lookup_failure)
            invalid[forbidden] = result[forbidden]
            with self.subTest(forbidden=forbidden):
                self.assertInvalid(invalid)
        wrong_action = copy.deepcopy(record)
        wrong_action["action_id"] = "ed3757ab-1268-4ce1-94f8-f37f30faf92d"
        with self.assertRaises(ContractSemanticError):
            _assert_reconciliation_matches(request, result, wrong_action)

    def test_success_after_timeout_requires_reconciled_record(self) -> None:
        direct = {"record_type": "action_transition", "from_status": "unknown", "to_status": "succeeded"}
        self.assertInvalid(direct)
        self.assertValid({"record_type": "action_transition", "from_status": "unknown", "to_status": "reconciling"})
        self.assertValid(
            {
                "record_type": "action_transition",
                "from_status": "reconciling",
                "to_status": "reconciled",
                "resolved_status": "succeeded",
                "reconciliation_evidence": _evidence_ref(),
            }
        )

    def test_retry_contract_accepts_only_reconciled_retryable_bounded_retry(self) -> None:
        previous = _navigation_request()
        new = _navigation_request(request_id=RETRY_REQUEST_ID, attempt=2, budget=0)
        authorization = _retry_authorization()
        self.assertValid(authorization)
        _assert_retry_semantics(previous, new, authorization)
        mutations = (
            ("reconciliation_completed", False),
            ("resolved_status", "unknown"),
            ("retry_budget_remaining", 0),
        )
        for field, value in mutations:
            invalid = copy.deepcopy(authorization)
            invalid[field] = value
            with self.subTest(field=field):
                self.assertInvalid(invalid)
        not_retryable = copy.deepcopy(authorization)
        not_retryable["error"]["retryable"] = False
        self.assertInvalid(not_retryable)

    def test_retry_semantics_reject_identity_and_attempt_bypass(self) -> None:
        previous = _navigation_request()
        authorization = _retry_authorization()
        same_request = _navigation_request(request_id=REQUEST_ID, attempt=2, budget=0)
        with self.assertRaises(ContractSemanticError):
            _assert_retry_semantics(previous, same_request, authorization)
        skipped_attempt = _navigation_request(request_id=RETRY_REQUEST_ID, attempt=3, budget=0)
        with self.assertRaises(ContractSemanticError):
            _assert_retry_semantics(previous, skipped_attempt, authorization)

    def test_verification_operational_success_is_distinct_from_verdict(self) -> None:
        self.assertValid(_verification_result("fail"))
        failed_operation = _verification_result("pass")
        failed_operation.update({"status": "failed", "result": "failure", "error": _error()})
        failed_operation.pop("verdict")
        failed_operation.pop("confidence")
        failed_operation.pop("evidence_refs")
        self.assertValid(failed_operation)
        for forbidden in ("verdict", "confidence", "mismatch_code"):
            invalid = copy.deepcopy(failed_operation)
            invalid[forbidden] = "pass" if forbidden == "verdict" else (0.5 if forbidden == "confidence" else "WRONG")
            with self.subTest(forbidden=forbidden):
                self.assertInvalid(invalid)

    def test_verification_is_deterministic_and_uncertain_never_passes(self) -> None:
        valid_request = _verification_request()
        valid_manifest = _manifest()
        first = _deterministic_verdict(valid_request, valid_manifest)
        second = _deterministic_verdict(copy.deepcopy(valid_request), copy.deepcopy(valid_manifest))
        self.assertEqual(first, "pass")
        self.assertEqual(first, second)
        mismatch_manifest = _manifest(_observation(part_id="wrong-part"))
        mismatch_request = _verification_request(_observation(part_id="wrong-part"))
        self.assertEqual(_deterministic_verdict(mismatch_request, mismatch_manifest), "fail")
        ambiguous = _observation("ambiguous")
        uncertain_request = _verification_request(ambiguous)
        uncertain_manifest = _manifest(ambiguous)
        self.assertEqual(_deterministic_verdict(uncertain_request, uncertain_manifest), "uncertain")
        self.assertNotEqual(_deterministic_verdict(uncertain_request, uncertain_manifest), "pass")

    def test_deadline_must_be_after_timestamp(self) -> None:
        request = _mission_request()
        request["deadline_at"] = request["timestamp"]
        self.assertValid(request)
        with self.assertRaises(ContractSemanticError):
            _assert_deadline_after_timestamp(request)


if __name__ == "__main__":
    unittest.main()
