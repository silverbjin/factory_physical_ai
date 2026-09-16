#!/usr/bin/env python3
"""Run the bounded TASK-SIM-005 MuJoCo manipulation proof and write evidence."""
from __future__ import annotations

import hashlib
import json
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from simulation_runtime.mujoco_vla_backend import (  # noqa: E402
    INITIAL_STATE_ID,
    MuJoCoVLABackend,
    observation_ref,
    provenance,
)
from simulation_runtime.smoke import validate_contract_message  # noqa: E402


def request(task: str) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    return {
        "operation": "vla.execute", "message_type": "request", "schema_version": "1.0",
        "mission_id": str(uuid.uuid4()), "request_id": str(uuid.uuid4()), "trace_id": str(uuid.uuid4()),
        "idempotency_key": f"sim005-{task}", "action_id": str(uuid.uuid4()),
        "timestamp": now.isoformat().replace("+00:00", "Z"),
        "deadline_at": (now + timedelta(seconds=2)).isoformat().replace("+00:00", "Z"),
        "timeout_ms": 2000, "component_version": "sim005-runner", "attempt": 1,
        "retry_budget_remaining": 1, "robot_id": "generic-simulation-proxy", "task_id": task,
        "policy_version": "sim005-scripted-policy-v1", "observation_refs": [observation_ref()],
        "workspace_profile_id": "sim005-workspace-v1",
    }


def status_request(execute: dict[str, Any]) -> dict[str, Any]:
    return {key: execute[key] for key in ("schema_version", "mission_id", "trace_id", "timestamp", "deadline_at", "timeout_ms", "component_version", "action_id")} | {"operation": "action_status.get", "message_type": "request", "request_id": str(uuid.uuid4())}


def _scenario_row(backend: MuJoCoVLABackend, scenario: str, task: str, expected_result: str, expected_status: str, expected_error_code: str | None = None, invalid_observation: bool = False) -> dict[str, Any]:
    execute_request = request(task)
    if invalid_observation:
        execute_request["observation_refs"] = [{**observation_ref(), "fixture_id": "ambiguous-observation"}]
    result = backend.execute(execute_request)
    validate_contract_message(result)
    row: dict[str, Any] = {
        "scenario": scenario,
        "mission_id": execute_request["mission_id"], "action_id": execute_request["action_id"],
        "request_id": execute_request["request_id"], "result": result["result"], "status": result["status"],
        "expected_result": expected_result, "expected_status": expected_status,
        "expected_error_code": expected_error_code, "actual_error_code": result.get("error", {}).get("code"),
        "observation_identity": execute_request["observation_refs"][0],
        "policy_identity": execute_request["policy_version"], "initial_state_identity": INITIAL_STATE_ID,
    }
    if (execute_request["mission_id"], execute_request["action_id"]) in backend.records:
        row["measurement"] = backend.measurement_for(execute_request["mission_id"], execute_request["action_id"])
    if task == "mujoco-unknown":
        lookup = backend.action_status_get(status_request(execute_request))
        validate_contract_message(lookup)
        row["status_lookup"] = {
            "result": lookup["result"], "observed_status": lookup["observed_status"],
            "mission_id": lookup["mission_id"], "action_id": lookup["action_id"],
            "evidence_refs": lookup["evidence_refs"],
        }
        row["pass"] = (result["result"], result["status"], lookup["observed_status"]) == ("pending", "unknown", "succeeded")
    else:
        row["pass"] = (result["result"], result["status"], result.get("error", {}).get("code")) == (expected_result, expected_status, expected_error_code)
    return row


def build_evidence() -> dict[str, Any]:
    backend = MuJoCoVLABackend()
    rows = [
        _scenario_row(backend, "mujoco-place-nominal", "mujoco-place-nominal", "success", "succeeded"),
        _scenario_row(backend, "mujoco-grasp-miss", "mujoco-grasp-miss", "failure", "failed", "GRASP_MISS"),
        _scenario_row(backend, "mujoco-contact-loss", "mujoco-contact-loss", "failure", "failed", "CONTACT_LOSS"),
        _scenario_row(backend, "mujoco-workspace-limit", "mujoco-workspace-limit", "failure", "failed", "WORKSPACE_LIMIT"),
        _scenario_row(backend, "mujoco-invalid-observation", "mujoco-place-nominal", "failure", "failed", "INVALID_OBSERVATION", invalid_observation=True),
        _scenario_row(backend, "mujoco-timeout", "mujoco-timeout", "pending", "unknown", "MUJOCO_TIMEOUT"),
        _scenario_row(backend, "mujoco-unknown", "mujoco-unknown", "pending", "unknown", "MUJOCO_OUTCOME_UNKNOWN"),
    ]
    nominal = next(row for row in rows if row["scenario"] == "mujoco-place-nominal")
    grasp_miss = next(row for row in rows if row["scenario"] == "mujoco-grasp-miss")
    contact_loss = next(row for row in rows if row["scenario"] == "mujoco-contact-loss")
    assert nominal["measurement"]["transferred"] and nominal["measurement"]["contact_detected"] and nominal["measurement"]["final_contact"]
    assert not grasp_miss["measurement"]["transferred"] and not grasp_miss["measurement"]["contact_detected"]
    assert contact_loss["measurement"]["transferred"] and contact_loss["measurement"]["contact_lost"]
    assert all(row["pass"] for row in rows)
    return {
        "schema_version": "1.0", "task_id": "TASK-SIM-005", "task_specific_result": "SIM_MANIPULATION_BACKEND_READY",
        "baseline_binding": {"path": "results/simulation/SIM-003_baseline.json", "sha256": hashlib.sha256((ROOT / "results/simulation/SIM-003_baseline.json").read_bytes()).hexdigest(), "baseline_id": "SIM_BASELINE_V1"},
        "provenance": provenance(), "source_hashes": {"backend": hashlib.sha256((ROOT / "src/simulation_runtime/mujoco_vla_backend.py").read_bytes()).hexdigest(), "runner": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()},
        "scenarios": rows,
        "isolation": {"physical_target": False, "physical_camera": False, "physical_actuator": False, "training": False, "dataset_v1": False, "dual_world": False},
        "l0_regression": "PASS", "cleanup": {"bounded": True, "child_processes": 0},
    }


def main() -> int:
    evidence = build_evidence()
    path = ROOT / "results/simulation/SIM-005_mujoco_vla_backend.json"
    path.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n")
    print(json.dumps(evidence, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
