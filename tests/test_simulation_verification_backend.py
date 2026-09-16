from __future__ import annotations

import json
import sys
import uuid
from dataclasses import replace
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
    assert source == "deterministic"
    return normalize_deterministic_observation(payload or {"quality": "valid", "part_id": "sim-workpiece", "location_id": "pickup-zone"}, fixture_id="deterministic-observation", fixture_version="1", timestamp="2026-09-16T00:00:00Z")


def accepted_gazebo_result() -> dict[str, object]:
    evidence = json.loads((ROOT / "results/simulation/SIM-004_navigation_backend.json").read_text())
    return next(scenario["result"] for scenario in evidence["scenarios"] if scenario["id"] == "success")


def accepted_mujoco_scenario() -> dict[str, object]:
    evidence = json.loads((ROOT / "results/simulation/SIM-005_mujoco_vla_backend.json").read_text())
    return next(scenario for scenario in evidence["scenarios"] if scenario["scenario"] == "mujoco-place-nominal")


def test_equivalent_deterministic_observations_produce_the_same_pass_verdict() -> None:
    observation = normalized(part_id="sim-workpiece", location_id="line-b-drop", quality="valid")
    observed_at = datetime.fromisoformat(observation.reference["timestamp"].replace("Z", "+00:00"))
    verification_request = request([observation.reference], timestamp=observed_at + timedelta(seconds=1))
    verification_request["expected_state"] = {"part_id": "sim-workpiece", "location_id": "line-b-drop"}
    result = VerificationBackend().verify(verification_request, [observation])
    validate_contract_message(result)
    assert result["verdict"] == "pass"


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
        normalize_gazebo_observation({"action_id": "x", "timestamp": "2026-09-16T00:00:00Z", "world_state": "hidden"})


def test_accepted_backend_shapes_fail_closed_without_semantic_state_and_preserve_identity() -> None:
    gazebo = normalize_gazebo_observation(accepted_gazebo_result())
    mujoco = normalize_mujoco_observation(accepted_mujoco_scenario())
    assert gazebo.payload == {"quality": "insufficient"}
    assert mujoco.payload == {"quality": "insufficient"}
    assert gazebo.reference["content_sha256"] == accepted_gazebo_result()["evidence_refs"][0]["sha256"]
    assert mujoco.reference["content_sha256"] == accepted_mujoco_scenario()["observation_identity"]["content_sha256"]
    backend = VerificationBackend()
    for observation in (gazebo, mujoco):
        observed_at = datetime.fromisoformat(observation.reference["timestamp"].replace("Z", "+00:00"))
        verification_request = request([observation.reference], timestamp=observed_at + timedelta(seconds=1))
        verification_request["expected_state"] = {"part_id": "sim-workpiece", "location_id": "line-b-drop"}
        assert backend.verify(verification_request, [observation])["verdict"] == "uncertain"
    failed = dict(accepted_gazebo_result(), result="failure", status="failed")
    assert normalize_gazebo_observation(failed).payload == {"quality": "insufficient"}


def test_observation_and_accepted_provenance_are_immutable_and_tampering_fails_closed() -> None:
    observation = normalize_gazebo_observation(accepted_gazebo_result())
    request_time = datetime.fromisoformat(observation.reference["timestamp"].replace("Z", "+00:00")) + timedelta(seconds=1)
    with pytest.raises(TypeError):
        observation.reference["fixture_id"] = "forged"
    with pytest.raises(TypeError):
        observation.provenance["backend_id"] = "forged"
    with pytest.raises(TypeError):
        observation.payload |= {"part_id": "forged"}
    forged = replace(observation, provenance={**observation.provenance, "backend_id": "forged"})
    decision = VerificationBackend().verify_with_route(request([forged.reference], timestamp=request_time), [forged])
    assert decision.result["result"] == "failure"
    assert decision.route == "HITL"
    forged_reference = replace(observation, reference={**observation.reference, "content_sha256": "0" * 64})
    decision = VerificationBackend().verify_with_route(request([forged_reference.reference], timestamp=request_time), [forged_reference])
    assert decision.result["result"] == "failure"
    assert decision.route == "HITL"
