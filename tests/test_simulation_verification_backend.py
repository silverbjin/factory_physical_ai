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
import simulation_runtime.verification_backend as verification_backend_module  # noqa: E402
from simulation_runtime.smoke import canonical_sha256, validate_contract_message  # noqa: E402


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


def accepted_gazebo_result(scenario_id: str = "success") -> dict[str, object]:
    evidence = json.loads((ROOT / "results/simulation/SIM-004_navigation_backend.json").read_text())
    return next(scenario["result"] for scenario in evidence["scenarios"] if scenario["id"] == scenario_id)


def accepted_mujoco_scenario(scenario_name: str = "mujoco-place-nominal") -> dict[str, object]:
    evidence = json.loads((ROOT / "results/simulation/SIM-005_mujoco_vla_backend.json").read_text())
    return next(scenario for scenario in evidence["scenarios"] if scenario["scenario"] == scenario_name)


def accepted_observations() -> tuple[object, object]:
    return (
        normalize_gazebo_observation(accepted_gazebo_result()),
        normalize_mujoco_observation(accepted_mujoco_scenario()),
    )


def verify_observation(observation: object) -> object:
    observed_at = datetime.fromisoformat(observation.reference["timestamp"].replace("Z", "+00:00"))
    return VerificationBackend().verify_with_route(
        request([observation.reference], timestamp=observed_at + timedelta(seconds=1)),
        [observation],
    )


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


def test_t1_normalized_hash_is_derived_from_normalized_content() -> None:
    for observation in accepted_observations():
        assert observation.reference["content_sha256"] == canonical_sha256(dict(observation.payload))


def test_t2_upstream_provenance_is_preserved_separately() -> None:
    gazebo, mujoco = accepted_observations()
    assert dict(gazebo.source_identity) == accepted_gazebo_result()["evidence_refs"][0]
    assert dict(mujoco.source_identity) == accepted_mujoco_scenario()["observation_identity"]
    for observation in (gazebo, mujoco):
        assert dict(observation.source_identity) != dict(observation.reference)
        assert observation.reference["content_sha256"] == canonical_sha256(dict(observation.payload))


def test_t3_normalized_payload_tampering_fails_closed() -> None:
    for observation in accepted_observations():
        forged = replace(observation, payload={"quality": "valid", "part_id": "sim-workpiece", "location_id": "pickup-zone"})
        observed_at = datetime.fromisoformat(forged.reference["timestamp"].replace("Z", "+00:00"))
        decision = VerificationBackend().verify_with_route(request([forged.reference], timestamp=observed_at + timedelta(seconds=1)), [forged])
        assert decision.result["result"] == "failure"
        assert decision.route == "HITL"


def test_t4_normalized_hash_tampering_fails_closed() -> None:
    for observation in accepted_observations():
        forged_reference = {**observation.reference, "content_sha256": "0" * 64}
        forged = replace(observation, reference=forged_reference, source_identity=forged_reference)
        observed_at = datetime.fromisoformat(forged.reference["timestamp"].replace("Z", "+00:00"))
        decision = VerificationBackend().verify_with_route(request([forged.reference], timestamp=observed_at + timedelta(seconds=1)), [forged])
        assert decision.result["result"] == "failure"
        assert decision.route == "HITL"


def test_t5_source_provenance_tampering_fails_closed() -> None:
    for observation in accepted_observations():
        forged = replace(observation, source_identity={"forged": "identity"})
        observed_at = datetime.fromisoformat(forged.reference["timestamp"].replace("Z", "+00:00"))
        decision = VerificationBackend().verify_with_route(request([forged.reference], timestamp=observed_at + timedelta(seconds=1)), [forged])
        assert decision.result["result"] == "failure"
        assert decision.route == "HITL"


def test_t5_gazebo_valid_but_wrong_accepted_identity_substitution_fails_closed() -> None:
    observation = normalize_gazebo_observation(accepted_gazebo_result("success"))
    wrong_identity = accepted_gazebo_result("invalid_goal")["evidence_refs"][0]
    forged = replace(observation, source_identity=wrong_identity)
    decision = verify_observation(forged)
    assert decision.result["result"] == "failure"
    assert decision.route == "HITL"


def test_t5_mujoco_valid_but_wrong_accepted_identity_substitution_fails_closed() -> None:
    observation = normalize_mujoco_observation(accepted_mujoco_scenario("mujoco-place-nominal"))
    wrong_identity = accepted_mujoco_scenario("mujoco-invalid-observation")["observation_identity"]
    forged = replace(observation, source_identity=wrong_identity)
    decision = verify_observation(forged)
    assert decision.result["result"] == "failure"
    assert decision.route == "HITL"


def test_t6_coordinated_tampering_fails_closed() -> None:
    observation, _ = accepted_observations()
    forged_payload = {"quality": "valid", "part_id": "sim-workpiece", "location_id": "pickup-zone"}
    forged_reference = {**observation.reference, "content_sha256": canonical_sha256(forged_payload)}
    forged = replace(observation, payload=forged_payload, reference=forged_reference, source_identity=forged_reference)
    observed_at = datetime.fromisoformat(forged.reference["timestamp"].replace("Z", "+00:00"))
    decision = VerificationBackend().verify_with_route(request([forged.reference], timestamp=observed_at + timedelta(seconds=1)), [forged])
    assert decision.result["result"] == "failure"
    assert decision.route == "HITL"


def test_t6_gazebo_coordinated_valid_provenance_substitution_fails_closed() -> None:
    observation = normalize_gazebo_observation(accepted_gazebo_result("success"))
    wrong_record = accepted_gazebo_result("invalid_goal")
    assert "record_sha256" in observation.provenance
    wrong_provenance = {**observation.provenance, "record_sha256": canonical_sha256(wrong_record)}
    forged = replace(observation, provenance=wrong_provenance, source_identity=wrong_record["evidence_refs"][0])
    decision = verify_observation(forged)
    assert decision.result["result"] == "failure"
    assert decision.route == "HITL"


def test_t6_mujoco_coordinated_valid_provenance_substitution_fails_closed() -> None:
    observation = normalize_mujoco_observation(accepted_mujoco_scenario("mujoco-place-nominal"))
    wrong_record = accepted_mujoco_scenario("mujoco-invalid-observation")
    assert "record_sha256" in observation.provenance
    wrong_provenance = {**observation.provenance, "record_sha256": canonical_sha256(wrong_record)}
    forged = replace(observation, provenance=wrong_provenance, source_identity=wrong_record["observation_identity"])
    decision = verify_observation(forged)
    assert decision.result["result"] == "failure"
    assert decision.route == "HITL"


def test_t7_real_accepted_backend_shapes_are_required_for_adaptation() -> None:
    forged_gazebo = dict(accepted_gazebo_result())
    forged_gazebo["evidence_refs"] = [{"uri": "urn:factory-evidence:forged", "sha256": "0" * 64}]
    forged_mujoco = dict(accepted_mujoco_scenario())
    forged_mujoco["observation_identity"] = {**forged_mujoco["observation_identity"], "content_sha256": "0" * 64}
    with pytest.raises(ValueError):
        normalize_gazebo_observation(forged_gazebo)
    with pytest.raises(ValueError):
        normalize_mujoco_observation(forged_mujoco)


def test_record_binding_rejects_no_match_and_ambiguous_match(monkeypatch: pytest.MonkeyPatch) -> None:
    accepted = accepted_mujoco_scenario()
    no_match = {**accepted, "request_id": "00000000-0000-4000-8000-000000000000"}
    with pytest.raises(ValueError, match="exactly one"):
        verification_backend_module._match_accepted_record("mujoco", no_match)
    monkeypatch.setattr(verification_backend_module, "_accepted_records", lambda source: (accepted, accepted))
    with pytest.raises(ValueError, match="exactly one"):
        verification_backend_module._match_accepted_record("mujoco", accepted)


def test_valid_same_record_binding_is_preserved_and_accepted() -> None:
    gazebo_record = accepted_gazebo_result()
    mujoco_record = accepted_mujoco_scenario()
    for observation, record in (
        (normalize_gazebo_observation(gazebo_record), gazebo_record),
        (normalize_mujoco_observation(mujoco_record), mujoco_record),
    ):
        assert observation.provenance["record_sha256"] == canonical_sha256(record)
        decision = verify_observation(observation)
        assert decision.result["result"] == "success"
        assert decision.result["verdict"] == "uncertain"
        assert decision.route == "RECONCILE"


def test_accepted_backend_shapes_fail_closed_without_semantic_state() -> None:
    gazebo, mujoco = accepted_observations()
    assert gazebo.payload == {"quality": "insufficient"}
    assert mujoco.payload == {"quality": "insufficient"}
    backend = VerificationBackend()
    for observation in (gazebo, mujoco):
        observed_at = datetime.fromisoformat(observation.reference["timestamp"].replace("Z", "+00:00"))
        verification_request = request([observation.reference], timestamp=observed_at + timedelta(seconds=1))
        verification_request["expected_state"] = {"part_id": "sim-workpiece", "location_id": "line-b-drop"}
        assert backend.verify(verification_request, [observation])["verdict"] == "uncertain"


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
