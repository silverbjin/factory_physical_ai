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
    source_identity: FrozenDict

    def __post_init__(self) -> None:
        object.__setattr__(self, "reference", _frozen(self.reference))
        object.__setattr__(self, "payload", _frozen(self.payload))
        object.__setattr__(self, "provenance", _frozen(self.provenance))
        object.__setattr__(self, "source_identity", _frozen(self.source_identity))


@dataclass(frozen=True)
class VerificationDecision:
    result: dict[str, Any]
    route: str


def _normalized(
    source: str,
    payload: Mapping[str, str],
    *,
    fixture_id: str,
    fixture_version: str,
    timestamp: str,
    content_sha256: str | None = None,
) -> NormalizedObservation:
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
    identity_hash = content_sha256 or canonical_sha256(material)
    if len(identity_hash) != 64 or any(character not in "0123456789abcdef" for character in identity_hash):
        raise ValueError("observation content hash is malformed")
    reference = {"fixture_set_id": "SIM_FIXTURE_SET_V1", "fixture_id": fixture_id, "fixture_version": fixture_version, "content_sha256": identity_hash, "timestamp": timestamp, "source_kind": "mock"}
    return NormalizedObservation(reference, material, source, {"source": source, **_ACCEPTED_PROVENANCE[source]}, reference)


def normalize_deterministic_observation(observation: Mapping[str, str], **identity: str) -> NormalizedObservation:
    return _normalized("deterministic", observation, **identity)


def normalize_gazebo_observation(navigation_result: Mapping[str, Any]) -> NormalizedObservation:
    """Adapt a public SIM-004 ``navigation.execute`` result, not world state."""
    allowed = {"action_id", "arrival", "component_version", "evidence_refs", "message_type", "mission_id", "operation", "request_id", "result", "schema_version", "source_kind", "status", "timestamp", "trace_id"}
    if set(navigation_result) - allowed:
        raise ValueError("SIM-004 navigation result contains forbidden hidden-state fields")
    evidence_refs = navigation_result.get("evidence_refs")
    timestamp, action_id = str(navigation_result.get("timestamp", "")), str(navigation_result.get("action_id", ""))
    if not action_id:
        raise ValueError("SIM-004 navigation result requires action_id")
    if not isinstance(evidence_refs, Sequence) or isinstance(evidence_refs, (str, bytes)) or len(evidence_refs) != 1 or not isinstance(evidence_refs[0], Mapping):
        raise ValueError("SIM-004 navigation result requires exactly one immutable evidence reference")
    evidence_hash = evidence_refs[0].get("sha256")
    if not isinstance(evidence_hash, str):
        raise ValueError("SIM-004 navigation evidence hash is malformed")
    # SIM-004 proves arrival at a destination but does not observe a part.  It
    # therefore cannot establish the complete expected state for a pass.
    return _normalized("gazebo", {"quality": "insufficient"}, fixture_id=f"gazebo-navigation-{action_id}", fixture_version="sim004-navigation-backend-v2", timestamp=timestamp, content_sha256=evidence_hash)


def normalize_mujoco_observation(scenario: Mapping[str, Any]) -> NormalizedObservation:
    """Adapt a public SIM-005 scenario record, never MuJoCo model state."""
    allowed = {"action_id", "actual_error_code", "expected_error_code", "expected_result", "expected_status", "initial_state_identity", "measurement", "mission_id", "observation_identity", "pass", "policy_identity", "request_id", "result", "scenario", "status", "status_lookup"}
    if set(scenario) - allowed:
        raise ValueError("SIM-005 scenario contains forbidden hidden-state fields")
    identity = scenario.get("observation_identity")
    if not isinstance(identity, Mapping):
        raise ValueError("SIM-005 scenario requires observation_identity")
    fixture_id, fixture_version, timestamp, content_sha256 = (identity.get("fixture_id"), identity.get("fixture_version"), identity.get("timestamp"), identity.get("content_sha256"))
    if identity.get("fixture_set_id") != "SIM_FIXTURE_SET_V1" or identity.get("source_kind") != "mock" or not all(isinstance(value, str) and value for value in (fixture_id, fixture_version, timestamp, content_sha256)):
        raise ValueError("SIM-005 observation identity is malformed")
    # SIM-005 exposes manipulation success evidence, not semantic part or
    # location state.  Preserve its identity but fail closed as insufficient.
    return _normalized("mujoco", {"quality": "insufficient"}, fixture_id=fixture_id, fixture_version=fixture_version, timestamp=timestamp, content_sha256=content_sha256)


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
            if dict(observation.reference) != dict(observation.source_identity):
                raise ContractViolation("normalized reference does not preserve source identity")
            if observation.source not in _SOURCES or dict(observation.provenance) != {"source": observation.source, **_ACCEPTED_PROVENANCE[observation.source]}:
                raise ContractViolation("unaccepted backend provenance")
            if observation.source == "deterministic" and canonical_sha256(dict(observation.payload)) != observation.reference["content_sha256"]:
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
