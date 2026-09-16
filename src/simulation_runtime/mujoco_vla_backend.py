"""Bounded MuJoCo manipulation proxy behind the frozen VLA Skill contract.

The model is deliberately generic: it is not a physical robot target and this
module exposes no joint, gripper, trajectory, or hardware-control interface.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import mujoco

from .smoke import ContractViolation, canonical_sha256, validate_contract_message

ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "configs/simulation/sim005_mujoco_manipulation.yaml"
MODEL_PATH = ROOT / "data/simulation/sim005_mujoco_manipulation.xml"
COMPONENT_VERSION = "sim005-mujoco-vla-backend-v1"
INITIAL_STATE_ID = "sim005-seed-5005-workpiece-origin-v1"
OBSERVATION = {"quality": "valid", "part_id": "sim-workpiece", "location_id": "pickup-zone"}
TASKS = {"mujoco-place-nominal", "mujoco-grasp-miss", "mujoco-contact-loss", "mujoco-workspace-limit", "mujoco-timeout", "mujoco-unknown"}


@dataclass(frozen=True)
class ActionRecord:
    mission_id: str
    action_id: str
    observed_status: str
    recorded_at: str
    measurement_json: str


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _error(code: str, message: str, category: str, retryable: bool = False) -> dict[str, Any]:
    return {"code": code, "message": message, "category": category, "retryable": retryable}


def observation_ref() -> dict[str, str]:
    return {"fixture_set_id": "SIM_FIXTURE_SET_V1", "fixture_id": "mujoco-observation-v1", "fixture_version": "1", "content_sha256": canonical_sha256(OBSERVATION), "timestamp": "2026-09-16T00:00:00Z", "source_kind": "mock"}


@dataclass
class MuJoCoVLABackend:
    """Contract adapter with bounded private MuJoCo execution and status records."""
    records: dict[tuple[str, str], ActionRecord] = field(default_factory=dict)

    def execute(self, request: dict[str, Any]) -> dict[str, Any]:
        try:
            validate_contract_message(request)
        except ContractViolation as exc:
            return self._failure(request, "INVALID_VLA_REQUEST", str(exc), "VALIDATION")
        if request.get("operation") != "vla.execute":
            return self._failure(request, "INVALID_OPERATION", "vla.execute required", "VALIDATION")
        if request["task_id"] not in TASKS or request["policy_version"] != "sim005-scripted-policy-v1" or request["workspace_profile_id"] != "sim005-workspace-v1":
            return self._failure(request, "UNAPPROVED_SKILL", "task, policy, or workspace is not allowlisted", "VALIDATION")
        if request["observation_refs"] != [observation_ref()]:
            return self._failure(request, "INVALID_OBSERVATION", "observation identity is missing, stale, or ambiguous", "VALIDATION")
        task = request["task_id"]
        if task == "mujoco-timeout":
            self._record(request, "unknown", {"scenario": task, "physics_started": False, "reason": "bounded_timeout"})
            return self._result(request, "unknown", "pending", "uncertain", error=_error("MUJOCO_TIMEOUT", "bounded physics budget expired", "MODEL_TIMEOUT", True))
        if task == "mujoco-unknown":
            self._record(request, "succeeded", {"scenario": task, "physics_started": True, "authoritative_outcome": "succeeded"})
            return self._result(request, "unknown", "pending", "uncertain", error=_error("MUJOCO_OUTCOME_UNKNOWN", "result requires authoritative reconciliation", "DEPENDENCY_TIMEOUT", True))
        if task == "mujoco-workspace-limit":
            self._record(request, "failed", {"scenario": task, "physics_started": False, "workspace_limit_enforced": True})
            return self._failure(request, "WORKSPACE_LIMIT", "scripted command exceeds bounded workspace", "SAFETY_POLICY")
        measured = self._step_physics(task)
        if task == "mujoco-place-nominal" and measured["transferred"] and measured["contact_detected"] and measured["final_contact"]:
            self._record(request, "succeeded", measured)
            return self._result(request, "succeeded", "success", "succeeded", verifier_input_refs=[self._evidence_ref(request["action_id"])])
        if task == "mujoco-grasp-miss" and not measured["contact_detected"] and not measured["transferred"]:
            code, message = "GRASP_MISS", "measured pusher/workpiece contact was absent"
        elif task == "mujoco-contact-loss" and measured["contact_lost"] and measured["transferred"]:
            code, message = "CONTACT_LOSS", "measured pusher/workpiece contact was lost after transfer"
        else:
            code, message = "MANIPULATION_OBJECTIVE_UNMET", "measured manipulation state did not meet the objective"
        self._record(request, "failed", measured)
        return self._failure(request, code, message, "EXECUTION_FAILED")

    def action_status_get(self, request: dict[str, Any]) -> dict[str, Any]:
        try:
            validate_contract_message(request)
        except ContractViolation as exc:
            return self._status_failure(request, "INVALID_STATUS_REQUEST", str(exc), "VALIDATION")
        action_id = request.get("action_id")
        record = self.records.get((request.get("mission_id"), action_id))
        if request.get("operation") != "action_status.get" or record is None:
            return self._status_failure(request, "ACTION_NOT_FOUND", "no authoritative MuJoCo action record", "RESOURCE_UNAVAILABLE")
        return {"operation": "action_status.get", "message_type": "result", "schema_version": "1.0", "mission_id": request["mission_id"], "request_id": request["request_id"], "trace_id": request["trace_id"], "action_id": action_id, "timestamp": _now(), "component_version": COMPONENT_VERSION, "source_kind": "mock", "status": "succeeded", "result": "success", "observed_at": record.recorded_at, "observed_status": record.observed_status, "evidence_refs": [self._evidence_ref(action_id, request["mission_id"])]}

    def _step_physics(self, task: str) -> dict[str, float | int | bool | str]:
        model = mujoco.MjModel.from_xml_path(str(MODEL_PATH)); data = mujoco.MjData(model)
        pusher_body = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, "generic_pusher")
        workpiece_body = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, "workpiece")
        profiles = {
            "mujoco-place-nominal": (0.0, ((0.17, 400),)),
            "mujoco-grasp-miss": (0.12, ((0.17, 400),)),
            "mujoco-contact-loss": (0.0, ((0.20, 200), (0.0, 200))),
        }
        initial_y, commands = profiles[task]
        data.qpos[2] = initial_y
        mujoco.mj_forward(model, data)
        contact_detected = False
        steps = 0
        for control, budget in commands:
            data.ctrl[0] = control
            for _ in range(budget):
                mujoco.mj_step(model, data); steps += 1
                contact_detected = contact_detected or any(
                    {int(model.geom_bodyid[data.contact[index].geom1]), int(model.geom_bodyid[data.contact[index].geom2])} == {pusher_body, workpiece_body}
                    for index in range(data.ncon)
                )
        final_contact = any(
            {int(model.geom_bodyid[data.contact[index].geom1]), int(model.geom_bodyid[data.contact[index].geom2])} == {pusher_body, workpiece_body}
            for index in range(data.ncon)
        )
        object_x = float(data.qpos[1])
        return {"scenario": task, "object_x_before": 0.0, "object_x_after": object_x, "object_y_initial": initial_y, "transferred": object_x >= 0.035, "contact_detected": contact_detected, "final_contact": final_contact, "contact_lost": contact_detected and not final_contact, "steps": steps, "timestep_seconds": float(model.opt.timestep)}

    def _record(self, request: dict[str, Any], observed_status: str, measurement: dict[str, Any]) -> None:
        record = ActionRecord(request["mission_id"], request["action_id"], observed_status, _now(), json.dumps(measurement, sort_keys=True, separators=(",", ":")))
        self.records[(record.mission_id, record.action_id)] = record

    def measurement_for(self, mission_id: str, action_id: str) -> dict[str, Any]:
        record = self.records[(mission_id, action_id)]
        return json.loads(record.measurement_json)

    def _evidence_ref(self, action_id: str, mission_id: str | None = None) -> dict[str, str]:
        if mission_id is None:
            matching = [record for (record_mission_id, record_action_id), record in self.records.items() if record_action_id == action_id]
            if len(matching) != 1:
                raise ContractViolation("action evidence requires a unique mission-bound action record")
            record = matching[0]
        else:
            record = self.records[(mission_id, action_id)]
        immutable_payload = {"mission_id": record.mission_id, "action_id": record.action_id, "observed_status": record.observed_status, "recorded_at": record.recorded_at, "component_version": COMPONENT_VERSION, "measurement": json.loads(record.measurement_json)}
        return {"uri": f"urn:factory-evidence:sim-005:{record.mission_id}:{record.action_id}", "sha256": canonical_sha256(immutable_payload)}

    def _result(self, request: dict[str, Any], status: str, result: str, outcome: str, **extra: Any) -> dict[str, Any]:
        payload = {"operation": "vla.execute", "message_type": "result", "schema_version": "1.0", "mission_id": request["mission_id"], "request_id": request["request_id"], "trace_id": request["trace_id"], "action_id": request["action_id"], "timestamp": _now(), "component_version": COMPONENT_VERSION, "source_kind": "mock", "status": status, "result": result, "skill_outcome": outcome, "latency_ms": 800}
        payload.update(extra); validate_contract_message(payload); return payload

    def _failure(self, request: dict[str, Any], code: str, message: str, category: str) -> dict[str, Any]:
        if not {"mission_id", "request_id", "trace_id", "action_id"} <= request.keys(): raise ContractViolation(message)
        return self._result(request, "failed", "failure", "failed", error=_error(code, message, category))

    def _status_failure(self, request: dict[str, Any], code: str, message: str, category: str) -> dict[str, Any]:
        if not {"mission_id", "request_id", "trace_id", "action_id"} <= request.keys(): raise ContractViolation(message)
        return {"operation": "action_status.get", "message_type": "result", "schema_version": "1.0", "mission_id": request["mission_id"], "request_id": request["request_id"], "trace_id": request["trace_id"], "action_id": request["action_id"], "timestamp": _now(), "component_version": COMPONENT_VERSION, "source_kind": "mock", "status": "failed", "result": "failure", "error": _error(code, message, category)}


def provenance() -> dict[str, Any]:
    return {"baseline_id": "SIM_BASELINE_V1", "backend_id": COMPONENT_VERSION, "model_kind": "generic_simulation_proxy_manipulator", "physical_target": False, "initial_state_id": INITIAL_STATE_ID, "seed": 5005, "maximum_steps": 400, "timestep_seconds": 0.002, "mujoco_version": mujoco.__version__, "assets": [{"path": str(path.relative_to(ROOT)), "sha256": _sha(path)} for path in (CONFIG_PATH, MODEL_PATH, Path(__file__))]}
