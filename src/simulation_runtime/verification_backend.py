"""Simulator-neutral adapter and executor for ``verification.verify``.

Only immutable adapter output reaches the verifier. Gazebo and MuJoCo input is
limited to the public accepted result records; no simulator runtime is queried.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Mapping, Sequence

from .smoke import ContractViolation, canonical_sha256, validate_contract_message

COMPONENT_VERSION = "sim006-verification-backend-v1"
VALIDITY_WINDOW = timedelta(minutes=5)
_SOURCES = frozenset({"deterministic", "gazebo", "mujoco"})
_PAYLOAD_FIELDS = frozenset({"quality", "part_id", "location_id"})
_ACCEPTED_PROVENANCE = {
    "deterministic": {"backend_id": "sim006-deterministic-adapter-v1", "accepted_task_id": "TASK-SIM-006", "accepted_commit": "local-fixture", "evidence_path": "deterministic-fixture", "evidence_sha256": "local-fixture"},
    "gazebo": {"backend_id": "sim004-gazebo-navigation-backend-v2", "accepted_task_id": "TASK-SIM-004", "accepted_commit": "b7e8266abd17f48c18cca94d9433db50fd55464d", "evidence_path": "results/simulation/SIM-004_navigation_backend.json", "evidence_sha256": "b4c0ce91dde6c2f92c57ea6a227149362279993dee0dec4fd1ab12877e73f1d9"},
    "mujoco": {"backend_id": "sim005-mujoco-vla-backend-v1", "accepted_task_id": "TASK-SIM-005", "accepted_commit": "542514a4d10bc03087834e8a5f672d53afe6aa21", "evidence_path": "results/simulation/SIM-005_mujoco_vla_backend.json", "evidence_sha256": "f4d41fdb1f13978e1b1e5c91b95e31b38a69825a0d432a8284ff7731a3beb84f"},
}


class FrozenDict(dict[str, str]):
    """JSON-schema-compatible mapping that cannot be changed after creation."""
    def _immutable(self, *_: object, **__: object) -> None:
        raise TypeError("normalized observation data is immutable")
    __setitem__ = __delitem__ = clear = pop = popitem = setdefault = update = __ior__ = _immutable


def _frozen(value: Mapping[str, object]) -> FrozenDict:
    return FrozenDict({str(key): str(item) for key, item in value.items()})


def _timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamp must be UTC")
    return parsed.astimezone(timezone.utc)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


@dataclass(frozen=True)
class NormalizedObservation:
    """Immutable contract evidence plus validated accepted-backend provenance."""
    reference: FrozenDict
    payload: FrozenDict
    source: str
    provenance: FrozenDict

    def __post_init__(self) -> None:
        object.__setattr__(self, "reference", _frozen(self.reference))
        object.__setattr__(self, "payload", _frozen(self.payload))
        object.__setattr__(self, "provenance", _frozen(self.provenance))


@dataclass(frozen=True)
class VerificationDecision:
    result: dict[str, Any]
    route: str


def _normalized(source: str, payload: Mapping[str, str], *, fixture_id: str, fixture_version: str, timestamp: str) -> NormalizedObservation:
    if source not in _SOURCES:
        raise ValueError("unsupported observation source")
    if not fixture_id.strip() or not fixture_version.strip():
        raise ValueError("fixture identity is required")
    _timestamp(timestamp)
    material = dict(payload)
    if set(material) - _PAYLOAD_FIELDS:
        raise ValueError("simulator-specific or hidden-state fields are forbidden")
    quality = material.get("quality")
    if quality not in {"valid", "insufficient", "ambiguous"}:
        raise ValueError("observation quality is invalid")
    if quality == "valid":
        if set(material) != _PAYLOAD_FIELDS or not material["part_id"].strip() or not material["location_id"].strip():
            raise ValueError("valid observations require exact part and location")
    elif set(material) != {"quality"}:
        raise ValueError("insufficient or ambiguous evidence must not assert state")
    reference = {"fixture_set_id": "SIM_FIXTURE_SET_V1", "fixture_id": fixture_id, "fixture_version": fixture_version, "content_sha256": canonical_sha256(material), "timestamp": timestamp, "source_kind": "mock"}
    return NormalizedObservation(reference, material, source, {"source": source, **_ACCEPTED_PROVENANCE[source]})


def normalize_deterministic_observation(observation: Mapping[str, str], **identity: str) -> NormalizedObservation:
    return _normalized("deterministic", observation, **identity)


def normalize_gazebo_observation(navigation_result: Mapping[str, Any], *, part_id: str) -> NormalizedObservation:
    """Adapt a public SIM-004 ``navigation.execute`` result, not world state."""
    allowed = {"action_id", "arrival", "component_version", "evidence_refs", "message_type", "mission_id", "operation", "request_id", "result", "schema_version", "source_kind", "status", "timestamp", "trace_id"}
    if set(navigation_result) - allowed:
        raise ValueError("SIM-004 navigation result contains forbidden hidden-state fields")
    arrival = navigation_result.get("arrival")
    valid = (navigation_result.get("operation") == "navigation.execute" and navigation_result.get("message_type") == "result" and navigation_result.get("schema_version") == "1.0" and navigation_result.get("source_kind") == "mock" and navigation_result.get("component_version") == "sim004-navigation-backend-v2" and navigation_result.get("result") == "success" and navigation_result.get("status") == "succeeded" and isinstance(arrival, Mapping) and arrival.get("verified") is True and isinstance(arrival.get("destination_id"), str) and bool(part_id.strip()))
    timestamp, action_id = str(navigation_result.get("timestamp", "")), str(navigation_result.get("action_id", ""))
    if not action_id:
        raise ValueError("SIM-004 navigation result requires action_id")
    payload: dict[str, str] = {"quality": "valid", "part_id": part_id, "location_id": str(arrival["destination_id"])} if valid else {"quality": "insufficient"}
    return _normalized("gazebo", payload, fixture_id=f"gazebo-navigation-{action_id}", fixture_version="sim004-navigation-backend-v2", timestamp=timestamp)


def normalize_mujoco_observation(scenario: Mapping[str, Any], *, part_id: str, location_id: str) -> NormalizedObservation:
    """Adapt a public SIM-005 scenario record, never MuJoCo model state."""
    allowed = {"action_id", "actual_error_code", "expected_error_code", "expected_result", "expected_status", "initial_state_identity", "measurement", "mission_id", "observation_identity", "pass", "policy_identity", "request_id", "result", "scenario", "status", "status_lookup"}
    if set(scenario) - allowed:
        raise ValueError("SIM-005 scenario contains forbidden hidden-state fields")
    measurement, identity = scenario.get("measurement"), scenario.get("observation_identity")
    valid = (scenario.get("result") == "success" and scenario.get("status") == "succeeded" and isinstance(measurement, Mapping) and measurement.get("transferred") is True and measurement.get("final_contact") is True and bool(part_id.strip()) and bool(location_id.strip()))
    if not isinstance(identity, Mapping):
        raise ValueError("SIM-005 scenario requires observation_identity")
    fixture_id, fixture_version, timestamp = identity.get("fixture_id"), identity.get("fixture_version"), identity.get("timestamp")
    if not all(isinstance(value, str) and value for value in (fixture_id, fixture_version, timestamp)):
        raise ValueError("SIM-005 observation identity is malformed")
    payload: dict[str, str] = {"quality": "valid", "part_id": part_id, "location_id": location_id} if valid else {"quality": "insufficient"}
    return _normalized("mujoco", payload, fixture_id=fixture_id, fixture_version=fixture_version, timestamp=timestamp)


class VerificationBackend:
    """Execute the frozen exact-match profile from normalized evidence alone."""
    def verify(self, request: Mapping[str, Any], observations: Sequence[NormalizedObservation], *, confidence: float | None = None) -> dict[str, Any]:
        return self.verify_with_route(request, observations, confidence=confidence).result

    def verify_with_route(self, request: Mapping[str, Any], observations: Sequence[NormalizedObservation], *, confidence: float | None = None) -> VerificationDecision:
        try:
            validate_contract_message(request)
            if request.get("operation") != "verification.verify":
                raise ContractViolation("verification.verify required")
            self._validate_evidence(request, observations)
        except (ContractViolation, KeyError, TypeError, ValueError) as exc:
            return VerificationDecision(self._failure(request, "INVALID_VERIFICATION_EVIDENCE", str(exc)), "HITL")
        payloads = [observation.payload for observation in observations]
        if len(payloads) != 1 or payloads[0]["quality"] != "valid":
            return VerificationDecision(self._success(request, "uncertain", observations, confidence), "RECONCILE")
        expected, payload = request["expected_state"], payloads[0]
        if payload["part_id"] != expected["part_id"] or payload["location_id"] != expected["location_id"]:
            return VerificationDecision(self._success(request, "fail", observations, confidence), "RECOVERY")
        return VerificationDecision(self._success(request, "pass", observations, confidence), "CONFIRMED")

    def _validate_evidence(self, request: Mapping[str, Any], observations: Sequence[NormalizedObservation]) -> None:
        references = request["observation_refs"]
        if len(references) != len(observations) or not observations:
            raise ContractViolation("every request reference must resolve exactly once")
        request_time = _timestamp(request["timestamp"])
        for reference, observation in zip(references, observations, strict=True):
            if not isinstance(observation, NormalizedObservation) or dict(reference) != dict(observation.reference):
                raise ContractViolation("observation identity, version, hash, or provenance mismatch")
            if observation.source not in _SOURCES or dict(observation.provenance) != {"source": observation.source, **_ACCEPTED_PROVENANCE[observation.source]}:
                raise ContractViolation("unaccepted backend provenance")
            if canonical_sha256(dict(observation.payload)) != observation.reference["content_sha256"]:
                raise ContractViolation("observation content hash mismatch")
            age = request_time - _timestamp(observation.reference["timestamp"])
            if age < timedelta(0) or age > VALIDITY_WINDOW:
                raise ContractViolation("observation is stale or from the future")

    def _success(self, request: Mapping[str, Any], verdict: str, observations: Sequence[NormalizedObservation], confidence: float | None) -> dict[str, Any]:
        if confidence is not None and not 0 <= confidence <= 1:
            raise ValueError("confidence must be in [0, 1]")
        default_confidence = {"pass": 1.0, "fail": 0.0, "uncertain": 0.0}[verdict]
        result: dict[str, Any] = {"operation": "verification.verify", "message_type": "result", "schema_version": "1.0", "mission_id": request["mission_id"], "request_id": request["request_id"], "trace_id": request["trace_id"], "action_id": request["action_id"], "timestamp": _now(), "component_version": COMPONENT_VERSION, "source_kind": "mock", "status": "succeeded", "result": "success", "verification_profile_version": "sim-exact-match-v1", "verdict": verdict, "confidence": default_confidence if verdict == "uncertain" else confidence if confidence is not None else default_confidence, "evidence_refs": [{"uri": f"urn:factory-evidence:sim-006:{observation.source}:{observation.reference['fixture_id']}", "sha256": observation.reference["content_sha256"]} for observation in observations]}
        if verdict != "pass":
            result["mismatch_code"] = "INSUFFICIENT_OR_AMBIGUOUS_EVIDENCE" if verdict == "uncertain" else "EXPECTED_STATE_MISMATCH"
        validate_contract_message(result)
        return result

    def _failure(self, request: Mapping[str, Any], code: str, message: str) -> dict[str, Any]:
        required = {"mission_id", "request_id", "trace_id", "action_id"}
        if not required <= request.keys():
            raise ContractViolation(message)
        result = {"operation": "verification.verify", "message_type": "result", "schema_version": "1.0", "mission_id": request["mission_id"], "request_id": request["request_id"], "trace_id": request["trace_id"], "action_id": request["action_id"], "timestamp": _now(), "component_version": COMPONENT_VERSION, "source_kind": "mock", "status": "failed", "result": "failure", "verification_profile_version": "sim-exact-match-v1", "error": {"code": code, "message": message or "verification evidence is invalid", "category": "DEPENDENCY_MALFORMED", "retryable": False}}
        validate_contract_message(result)
        return result
