from __future__ import annotations

import sys
import uuid
import importlib.util
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from simulation_runtime.mujoco_vla_backend import MuJoCoVLABackend, observation_ref, provenance  # noqa: E402
from simulation_runtime.smoke import validate_contract_message  # noqa: E402


def request(task: str = "mujoco-place-nominal") -> dict[str, object]:
    now = datetime.now(timezone.utc)
    return {"operation": "vla.execute", "message_type": "request", "schema_version": "1.0", "mission_id": str(uuid.uuid4()), "request_id": str(uuid.uuid4()), "trace_id": str(uuid.uuid4()), "idempotency_key": f"test-{task}", "action_id": str(uuid.uuid4()), "timestamp": now.isoformat().replace("+00:00", "Z"), "deadline_at": (now + timedelta(seconds=2)).isoformat().replace("+00:00", "Z"), "timeout_ms": 2000, "component_version": "test", "attempt": 1, "retry_budget_remaining": 1, "robot_id": "generic-simulation-proxy", "task_id": task, "policy_version": "sim005-scripted-policy-v1", "observation_refs": [observation_ref()], "workspace_profile_id": "sim005-workspace-v1"}


def status_request(execute: dict[str, object]) -> dict[str, object]:
    return {key: execute[key] for key in ("schema_version", "mission_id", "trace_id", "timestamp", "deadline_at", "timeout_ms", "component_version", "action_id")} | {"operation": "action_status.get", "message_type": "request", "request_id": str(uuid.uuid4())}


def test_nominal_runs_bounded_mujoco_physics_and_is_contract_valid() -> None:
    result = MuJoCoVLABackend().execute(request())
    validate_contract_message(result)
    assert result["result"] == "success" and result["status"] == "succeeded"


def test_grasp_miss_contact_loss_and_workspace_limit_fail_closed() -> None:
    backend = MuJoCoVLABackend()
    for task, code in (("mujoco-grasp-miss", "GRASP_MISS"), ("mujoco-contact-loss", "CONTACT_LOSS"), ("mujoco-workspace-limit", "WORKSPACE_LIMIT")):
        result = backend.execute(request(task))
        validate_contract_message(result)
        assert result["result"] == "failure" and result["error"]["code"] == code


def test_invalid_or_ambiguous_observation_is_never_success() -> None:
    req = request(); req["observation_refs"] = [{**observation_ref(), "fixture_id": "ambiguous-observation"}]
    result = MuJoCoVLABackend().execute(req)
    validate_contract_message(result)
    assert result["result"] == "failure" and result["error"]["code"] == "INVALID_OBSERVATION"


def test_timeout_and_unknown_require_status_lookup() -> None:
    backend = MuJoCoVLABackend()
    timeout = backend.execute(request("mujoco-timeout"))
    assert timeout["result"] == "pending" and timeout["status"] == "unknown"
    unknown_request = request("mujoco-unknown")
    unknown = backend.execute(unknown_request)
    lookup = backend.action_status_get(status_request(unknown_request))
    validate_contract_message(unknown); validate_contract_message(lookup)
    assert unknown["action_id"] == lookup["action_id"] and lookup["observed_status"] == "succeeded"


def test_status_lookup_rejects_action_record_from_another_mission() -> None:
    backend = MuJoCoVLABackend()
    executed = request("mujoco-unknown")
    backend.execute(executed)
    lookup_request = status_request(executed)
    lookup_request["mission_id"] = str(uuid.uuid4())

    result = backend.action_status_get(lookup_request)

    validate_contract_message(result)
    assert result["result"] == "failure"
    assert result["error"]["code"] == "ACTION_NOT_FOUND"


def test_scenario_outcomes_are_driven_by_measured_transfer_and_contact_state() -> None:
    backend = MuJoCoVLABackend()
    expected = {
        "mujoco-place-nominal": {"result": "success", "transferred": True, "contact_detected": True, "contact_lost": False},
        "mujoco-grasp-miss": {"result": "failure", "transferred": False, "contact_detected": False, "contact_lost": False},
        "mujoco-contact-loss": {"result": "failure", "transferred": True, "contact_detected": True, "contact_lost": True},
    }

    for task, expectation in expected.items():
        executed = request(task)
        result = backend.execute(executed)
        measurement = backend.measurement_for(executed["mission_id"], executed["action_id"])

        assert result["result"] == expectation["result"]
        assert measurement["transferred"] is expectation["transferred"]
        assert measurement["contact_detected"] is expectation["contact_detected"]
        assert measurement["contact_lost"] is expectation["contact_lost"]


def test_provenance_is_explicit_generic_and_hashed() -> None:
    info = provenance()
    assert info["baseline_id"] == "SIM_BASELINE_V1" and info["physical_target"] is False
    assert info["model_kind"] == "generic_simulation_proxy_manipulator"
    assert len(info["assets"]) == 3 and all(len(item["sha256"]) == 64 for item in info["assets"])


def test_evidence_builder_records_identities_measurements_and_invalid_observation() -> None:
    spec = importlib.util.spec_from_file_location("sim005_runner", ROOT / "scripts" / "run_simulation_mujoco_vla.py")
    assert spec and spec.loader
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)

    evidence = runner.build_evidence()

    invalid = next(row for row in evidence["scenarios"] if row["scenario"] == "mujoco-invalid-observation")
    nominal = next(row for row in evidence["scenarios"] if row["scenario"] == "mujoco-place-nominal")
    assert invalid["expected_error_code"] == "INVALID_OBSERVATION" and invalid["pass"] is True
    assert nominal["measurement"]["transferred"] is True and nominal["observation_identity"] == observation_ref()
    assert nominal["policy_identity"] == "sim005-scripted-policy-v1"
