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
    records: dict[str, str] = field(default_factory=dict)

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
            self.records[request["action_id"]] = "unknown"
            return self._result(request, "unknown", "pending", "uncertain", error=_error("MUJOCO_TIMEOUT", "bounded physics budget expired", "MODEL_TIMEOUT", True))
        if task == "mujoco-unknown":
            self.records[request["action_id"]] = "succeeded"
            return self._result(request, "unknown", "pending", "uncertain", error=_error("MUJOCO_OUTCOME_UNKNOWN", "result requires authoritative reconciliation", "DEPENDENCY_TIMEOUT", True))
        if task == "mujoco-workspace-limit":
            self.records[request["action_id"]] = "failed"
            return self._failure(request, "WORKSPACE_LIMIT", "scripted command exceeds bounded workspace", "SAFETY_POLICY")
        measured = self._step_physics()
        if task == "mujoco-place-nominal" and measured["object_x"] > 0.055:
            self.records[request["action_id"]] = "succeeded"
            return self._result(request, "succeeded", "success", "succeeded", verifier_input_refs=[self._evidence_ref(request["action_id"])])
        code = "GRASP_MISS" if task == "mujoco-grasp-miss" else "CONTACT_LOSS"
        self.records[request["action_id"]] = "failed"
        return self._failure(request, code, "measured object transfer did not meet the manipulation objective", "EXECUTION_FAILED")

    def action_status_get(self, request: dict[str, Any]) -> dict[str, Any]:
        try:
            validate_contract_message(request)
        except ContractViolation as exc:
            return self._status_failure(request, "INVALID_STATUS_REQUEST", str(exc), "VALIDATION")
        action_id = request.get("action_id")
        if request.get("operation") != "action_status.get" or action_id not in self.records:
            return self._status_failure(request, "ACTION_NOT_FOUND", "no authoritative MuJoCo action record", "RESOURCE_UNAVAILABLE")
        return {"operation": "action_status.get", "message_type": "result", "schema_version": "1.0", "mission_id": request["mission_id"], "request_id": request["request_id"], "trace_id": request["trace_id"], "action_id": action_id, "timestamp": _now(), "component_version": COMPONENT_VERSION, "source_kind": "mock", "status": "succeeded", "result": "success", "observed_at": _now(), "observed_status": self.records[action_id], "evidence_refs": [self._evidence_ref(action_id)]}

    def _step_physics(self) -> dict[str, float | int]:
        model = mujoco.MjModel.from_xml_path(str(MODEL_PATH)); data = mujoco.MjData(model)
        data.ctrl[0] = 0.30
        for _ in range(400): mujoco.mj_step(model, data)
        return {"object_x": float(data.qpos[1]), "steps": 400, "timestep_seconds": float(model.opt.timestep)}

    def _evidence_ref(self, action_id: str) -> dict[str, str]:
        return {"uri": f"urn:factory-evidence:sim-005:{action_id}", "sha256": hashlib.sha256(action_id.encode()).hexdigest()}

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
