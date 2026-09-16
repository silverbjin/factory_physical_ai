from __future__ import annotations

import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from simulation_runtime.verification_backend import (  # noqa: E402
    VerificationBackend,
    normalize_deterministic_observation,
    normalize_gazebo_observation,
    normalize_mujoco_observation,
)
from simulation_runtime.smoke import validate_contract_message  # noqa: E402


def request(observation_refs: list[dict[str, str]], *, timestamp: datetime | None = None) -> dict[str, object]:
    now = timestamp or datetime(2026, 9, 16, 0, 0, 1, tzinfo=timezone.utc)
    return {
        "operation": "verification.verify", "message_type": "request", "schema_version": "1.0",
        "mission_id": str(uuid.uuid4()), "request_id": str(uuid.uuid4()), "trace_id": str(uuid.uuid4()),
        "action_id": str(uuid.uuid4()), "timestamp": now.isoformat().replace("+00:00", "Z"),
        "deadline_at": (now + timedelta(seconds=1)).isoformat().replace("+00:00", "Z"),
        "timeout_ms": 1000, "component_version": "test", "verifier_id": "exact-state-verifier",
        "expected_state": {"part_id": "sim-workpiece", "location_id": "pickup-zone"},
        "observation_refs": observation_refs, "verification_profile_version": "sim-exact-match-v1",
    }


def normalized(source: str = "deterministic", **payload: str) -> object:
    adapter = {
        "deterministic": normalize_deterministic_observation,
        "gazebo": normalize_gazebo_observation,
        "mujoco": normalize_mujoco_observation,
    }[source]
    return adapter(payload or {"quality": "valid", "part_id": "sim-workpiece", "location_id": "pickup-zone"}, fixture_id=f"{source}-observation", fixture_version="1", timestamp="2026-09-16T00:00:00Z")


def test_equivalent_backend_observations_produce_the_same_pass_verdict() -> None:
    observations = [normalized(source) for source in ("deterministic", "gazebo", "mujoco")]
    backend = VerificationBackend()
    verdicts = []
    for observation in observations:
        result = backend.verify(request([observation.reference]), [observation])
        validate_contract_message(result)
        verdicts.append(result["verdict"])
    assert verdicts == ["pass", "pass", "pass"]


def test_mismatch_insufficient_and_ambiguous_evidence_never_pass() -> None:
    backend = VerificationBackend()
    mismatch = normalized(part_id="wrong-part", location_id="pickup-zone", quality="valid")
    insufficient = normalized(quality="insufficient")
    ambiguous = normalized(quality="ambiguous")
    assert backend.verify(request([mismatch.reference]), [mismatch])["verdict"] == "fail"
    assert backend.verify(request([insufficient.reference]), [insufficient])["verdict"] == "uncertain"
    assert backend.verify(request([ambiguous.reference]), [ambiguous])["verdict"] == "uncertain"


def test_stale_or_tampered_identity_fails_closed_and_routes_to_hitl() -> None:
    backend = VerificationBackend()
    observation = normalized()
    stale_request = request([observation.reference], timestamp=datetime(2026, 9, 16, 0, 10, tzinfo=timezone.utc))
    stale = backend.verify_with_route(stale_request, [observation])
    assert stale.result["result"] == "failure" and stale.route == "HITL"
    tampered_ref = {**observation.reference, "content_sha256": "0" * 64}
    tampered = backend.verify_with_route(request([tampered_ref]), [observation])
    assert tampered.result["result"] == "failure" and tampered.route == "HITL"


def test_confidence_cannot_promote_uncertain_and_routes_remain_separate() -> None:
    backend = VerificationBackend()
    observation = normalized(quality="insufficient")
    decision = backend.verify_with_route(request([observation.reference]), [observation], confidence=1.0)
    assert decision.result["verdict"] == "uncertain"
    assert decision.route == "RECONCILE"
    assert "route" not in decision.result


def test_adapter_rejects_hidden_state_and_malformed_payloads() -> None:
    with pytest.raises(ValueError):
        normalize_gazebo_observation(
            {"quality": "valid", "part_id": "sim-workpiece", "location_id": "pickup-zone", "world_state": "hidden"},
            fixture_id="gazebo-observation", fixture_version="1", timestamp="2026-09-16T00:00:00Z",
        )
