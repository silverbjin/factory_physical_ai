"""Simulator-neutral adapter and executor for ``verification.verify``.

The verifier consumes normalized, immutable observations only.  It has no
reference to Gazebo or MuJoCo runtime objects, which prevents hidden simulator
state from influencing a verdict.
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


def _timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamp must be UTC")
    return parsed.astimezone(timezone.utc)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


@dataclass(frozen=True)
class NormalizedObservation:
    """Contract evidence plus the adapter provenance that produced it."""

    reference: dict[str, str]
    payload: dict[str, str]
    source: str
    provenance: dict[str, str]


@dataclass(frozen=True)
class VerificationDecision:
    """A contract result and the separate executor-routing input."""

    result: dict[str, Any]
    route: str


def normalize_observation(
    source: str,
    observation: Mapping[str, str],
    *,
    fixture_id: str,
    fixture_version: str,
    timestamp: str,
    backend_id: str | None = None,
) -> NormalizedObservation:
    """Convert an adapter-provided observation into immutable contract evidence.

    Only the contract ObservationPayload fields are accepted.  In particular,
    simulator world/model state cannot cross this boundary.
    """
    if source not in _SOURCES:
        raise ValueError("unsupported observation source")
    if not fixture_id.strip() or not fixture_version.strip():
        raise ValueError("fixture identity is required")
    _timestamp(timestamp)
    payload = dict(observation)
    if set(payload) - _PAYLOAD_FIELDS:
        raise ValueError("simulator-specific or hidden-state fields are forbidden")
    quality = payload.get("quality")
    if quality not in {"valid", "insufficient", "ambiguous"}:
        raise ValueError("observation quality is invalid")
    if quality == "valid":
        if set(payload) != _PAYLOAD_FIELDS or not payload["part_id"].strip() or not payload["location_id"].strip():
            raise ValueError("valid observations require exact part and location")
    elif set(payload) != {"quality"}:
        raise ValueError("insufficient or ambiguous evidence must not assert state")
    reference = {
        "fixture_set_id": "SIM_FIXTURE_SET_V1",
        "fixture_id": fixture_id,
        "fixture_version": fixture_version,
        "content_sha256": canonical_sha256(payload),
        "timestamp": timestamp,
        "source_kind": "mock",
    }
    return NormalizedObservation(reference, payload, source, {"source": source, "backend_id": backend_id or f"sim006-{source}-adapter-v1"})


def normalize_deterministic_observation(observation: Mapping[str, str], **identity: str) -> NormalizedObservation:
    return normalize_observation("deterministic", observation, **identity)


def normalize_gazebo_observation(observation: Mapping[str, str], **identity: str) -> NormalizedObservation:
    return normalize_observation("gazebo", observation, **identity)


def normalize_mujoco_observation(observation: Mapping[str, str], **identity: str) -> NormalizedObservation:
    return normalize_observation("mujoco", observation, **identity)


class VerificationBackend:
    """Execute the frozen exact-match profile from normalized evidence alone."""

    def verify(
        self, request: Mapping[str, Any], observations: Sequence[NormalizedObservation], *, confidence: float | None = None
    ) -> dict[str, Any]:
        return self.verify_with_route(request, observations, confidence=confidence).result

    def verify_with_route(
        self, request: Mapping[str, Any], observations: Sequence[NormalizedObservation], *, confidence: float | None = None
    ) -> VerificationDecision:
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
        expected = request["expected_state"]
        payload = payloads[0]
        if payload["part_id"] != expected["part_id"] or payload["location_id"] != expected["location_id"]:
            return VerificationDecision(self._success(request, "fail", observations, confidence), "RECOVERY")
        return VerificationDecision(self._success(request, "pass", observations, confidence), "CONFIRMED")

    def _validate_evidence(self, request: Mapping[str, Any], observations: Sequence[NormalizedObservation]) -> None:
        references = request["observation_refs"]
        if len(references) != len(observations) or not observations:
            raise ContractViolation("every request reference must resolve exactly once")
        request_time = _timestamp(request["timestamp"])
        for reference, observation in zip(references, observations, strict=True):
            if reference != observation.reference:
                raise ContractViolation("observation identity, version, hash, or provenance mismatch")
            if canonical_sha256(observation.payload) != observation.reference["content_sha256"]:
                raise ContractViolation("observation content hash mismatch")
            age = request_time - _timestamp(observation.reference["timestamp"])
            if age < timedelta(0) or age > VALIDITY_WINDOW:
                raise ContractViolation("observation is stale or from the future")

    def _success(
        self, request: Mapping[str, Any], verdict: str, observations: Sequence[NormalizedObservation], confidence: float | None
    ) -> dict[str, Any]:
        if confidence is not None and not 0 <= confidence <= 1:
            raise ValueError("confidence must be in [0, 1]")
        default_confidence = {"pass": 1.0, "fail": 0.0, "uncertain": 0.0}[verdict]
        result: dict[str, Any] = {
            "operation": "verification.verify", "message_type": "result", "schema_version": "1.0",
            "mission_id": request["mission_id"], "request_id": request["request_id"], "trace_id": request["trace_id"],
            "action_id": request["action_id"], "timestamp": _now(), "component_version": COMPONENT_VERSION,
            "source_kind": "mock", "status": "succeeded", "result": "success",
            "verification_profile_version": "sim-exact-match-v1", "verdict": verdict,
            "confidence": default_confidence if verdict == "uncertain" else confidence if confidence is not None else default_confidence,
            "evidence_refs": [
                {"uri": f"urn:factory-evidence:sim-006:{observation.source}:{observation.reference['fixture_id']}", "sha256": observation.reference["content_sha256"]}
                for observation in observations
            ],
        }
        if verdict != "pass":
            result["mismatch_code"] = "INSUFFICIENT_OR_AMBIGUOUS_EVIDENCE" if verdict == "uncertain" else "EXPECTED_STATE_MISMATCH"
        validate_contract_message(result)
        return result

    def _failure(self, request: Mapping[str, Any], code: str, message: str) -> dict[str, Any]:
        required = {"mission_id", "request_id", "trace_id", "action_id"}
        if not required <= request.keys():
            raise ContractViolation(message)
        result = {
            "operation": "verification.verify", "message_type": "result", "schema_version": "1.0",
            "mission_id": request["mission_id"], "request_id": request["request_id"], "trace_id": request["trace_id"],
            "action_id": request["action_id"], "timestamp": _now(), "component_version": COMPONENT_VERSION,
            "source_kind": "mock", "status": "failed", "result": "failure",
            "verification_profile_version": "sim-exact-match-v1",
            "error": {"code": code, "message": message or "verification evidence is invalid", "category": "DEPENDENCY_MALFORMED", "retryable": False},
        }
        validate_contract_message(result)
        return result
