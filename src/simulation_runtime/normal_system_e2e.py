"""TASK-SIM-008's bounded canonical Gazebo system-world mission.

All public calls remain the frozen Simulation Lane envelopes.  The small
``GazeboWorldPort`` is private: its only mutable operation is invoked from the
``vla.execute`` adapter, so no actuator-shaped public API is introduced.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import time
import uuid
from typing import Any, Mapping, Protocol

from .mission_integration import COMPONENT_VERSION as PROFILE_COMPONENT_VERSION, select_profile
from .navigation_backend import NavigationBackend, RuntimeObservation
from .smoke import canonical_sha256, validate_contract_message
from .verification_backend import VerificationBackend, normalize_gazebo_system_observation

ROOT = Path(__file__).resolve().parents[2]
COMPONENT_VERSION = "sim008-normal-system-e2e-v1"
SCENARIO_PATH = ROOT / "configs/simulation/sim008_normal_system_scenario.json"


def _timestamp(now: datetime | None = None) -> str:
    return (now or datetime.now(timezone.utc)).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_scenario(path: Path = SCENARIO_PATH) -> dict[str, Any]:
    scenario = json.loads(path.read_text())
    required = {"scenario_id", "scenario_version", "profile", "world", "model", "object", "regions", "initial_state", "process_bounds_ms"}
    if set(scenario) != required or scenario["profile"] != "system":
        raise ValueError("canonical SIM-008 scenario is malformed")
    if set(scenario["regions"]) != {"source", "destination"}:
        raise ValueError("canonical SIM-008 regions are malformed")
    return scenario


class GazeboWorldPort(Protocol):
    """Private Gazebo-side world boundary; never exposed as a public Skill."""
    @property
    def ready(self) -> bool: ...
    def start(self) -> None: ...
    def bootstrap_localization(self) -> bool: ...
    def navigate(self, request: dict[str, Any]) -> RuntimeObservation: ...
    def reconcile(self, action_id: str) -> RuntimeObservation: ...
    def observe(self) -> Mapping[str, Any]: ...
    def apply_vla_surrogate(self, *, task_id: str, expected_from: Mapping[str, str], expected_to: Mapping[str, str]) -> bool: ...
    def close(self) -> bool: ...


@dataclass
class InMemoryGazeboWorld:
    """Deterministic test double for the private port, not runner evidence."""
    state: dict[str, str]
    ready: bool = True
    closed: bool = False
    calls: list[str] | None = None
    def __post_init__(self) -> None: self.calls = [] if self.calls is None else self.calls
    def start(self) -> None: self.calls.append("start")
    def bootstrap_localization(self) -> bool: self.calls.append("bootstrap"); return self.ready
    def navigate(self, request: dict[str, Any]) -> RuntimeObservation: self.calls.append(f"navigate:{request['destination_id']}"); return RuntimeObservation("succeeded", arrival_verified=True)
    def reconcile(self, action_id: str) -> RuntimeObservation: return RuntimeObservation("succeeded", arrival_verified=True)
    def observe(self) -> Mapping[str, str]: self.calls.append("observe"); return dict(self.state)
    def apply_vla_surrogate(self, *, task_id: str, expected_from: Mapping[str, str], expected_to: Mapping[str, str]) -> bool:
        self.calls.append("vla.execute")
        if task_id != "place-brake-ecu" or self.state != dict(expected_from): return False
        self.state = dict(expected_to); return True
    def close(self) -> bool: self.calls.append("close"); self.closed = True; return True


class NormalSystemE2E:
    def __init__(self, world: GazeboWorldPort, scenario: Mapping[str, Any] | None = None) -> None:
        self.scenario = dict(scenario or load_scenario())
        self.world = world
        self.lifecycle: dict[str, Any] = {"startup_attempted": False, "cleanup_complete": None}
        self.execution_started_at: datetime | None = None

    def _request(self, mission_id: str, trace_id: str, operation: str, *, action_id: str | None = None) -> dict[str, Any]:
        now = datetime.now(timezone.utc)
        request: dict[str, Any] = {"operation": operation, "message_type": "request", "schema_version": "1.0", "mission_id": mission_id, "request_id": str(uuid.uuid4()), "trace_id": trace_id, "timestamp": _timestamp(now), "deadline_at": _timestamp(now + timedelta(seconds=30)), "timeout_ms": 30000, "component_version": COMPONENT_VERSION}
        if operation == "mission.execute":
            source, destination = self.scenario["regions"]["source"]["id"], self.scenario["regions"]["destination"]["id"]
            request.update({"idempotency_key": f"{self.scenario['scenario_id']}:mission", "goal": {"mission_type": "line_side_supply", "priority": 50, "line_id": "line-b", "part_id": "brake-ecu-b", "quantity": 1, "source_id": source, "destination_id": destination, "approval_context": {"simulation_only": True, "approved": True, "authorized_by": "TASK-SIM-008"}}})
        elif operation in {"navigation.execute", "vla.execute"}:
            request.update({"idempotency_key": f"{self.scenario['scenario_id']}:{operation}:{action_id}", "action_id": action_id, "attempt": 1, "retry_budget_remaining": 0})
        elif operation == "verification.verify": request["action_id"] = action_id
        return request

    def _observation(self, mission_id: str, action_id: str) -> tuple[Any, dict[str, Any]]:
        raw = dict(self.world.observe())
        required = {"runtime_backend", "observation_source", "world_name", "entity_id", "entity_name", "pose", "semantic_state", "observed_at", "simulation_time", "snapshot_sha256"}
        if set(raw) != required:
            raise RuntimeError("authoritative Gazebo world observation is malformed")
        expected_world = Path(str(self.scenario["world"])).stem
        if raw["runtime_backend"] != "gz_sim_harmonic" or raw["world_name"] != expected_world:
            raise RuntimeError("authoritative Gazebo world identity mismatch")
        if raw["entity_id"] != self.scenario["object"]["id"]:
            raise RuntimeError("authoritative Gazebo entity identity mismatch")
        if raw["entity_name"] != self.scenario["object"]["gazebo_entity_name"]:
            raise RuntimeError("authoritative Gazebo entity name mismatch")
        expected_source = f"/world/{expected_world}/generate_world_sdf"
        if raw["observation_source"] != expected_source:
            raise RuntimeError("authoritative Gazebo observation source mismatch")
        semantic_state = raw["semantic_state"]
        pose, simulation_time = raw["pose"], raw["simulation_time"]
        if (not isinstance(semantic_state, Mapping) or set(semantic_state) != {"part_id", "location_id"} or
                not isinstance(pose, Mapping) or set(pose) != {"x", "y", "z"} or
                not all(isinstance(pose[key], (int, float)) for key in ("x", "y", "z")) or
                not isinstance(simulation_time, Mapping) or set(simulation_time) != {"sec", "nsec"} or
                not all(isinstance(simulation_time[key], int) and simulation_time[key] >= 0 for key in ("sec", "nsec")) or
                not isinstance(raw["snapshot_sha256"], str) or len(raw["snapshot_sha256"]) != 64):
            raise RuntimeError("authoritative Gazebo world observation is malformed")
        try:
            observed_at = datetime.fromisoformat(str(raw["observed_at"]).replace("Z", "+00:00"))
        except ValueError as exc:
            raise RuntimeError("authoritative Gazebo observation timestamp is malformed") from exc
        if (observed_at.tzinfo is None or self.execution_started_at is None or
                observed_at < self.execution_started_at or
                observed_at > datetime.now(timezone.utc) + timedelta(seconds=1)):
            raise RuntimeError("authoritative Gazebo observation is stale or outside the current execution")
        payload = {"quality": "valid", **dict(semantic_state)}
        identity = {"fixture_set_id": "SIM_FIXTURE_SET_V1", "fixture_id": f"sim008-gazebo-{action_id}", "fixture_version": self.scenario["scenario_version"], "content_sha256": canonical_sha256(payload), "timestamp": str(raw["observed_at"]), "source_kind": "mock"}
        record = {"integrated_world": "gazebo_harmonic", "mujoco_live_world": False, "mission_id": mission_id, "observation": payload, "observation_identity": identity, "authoritative_world_observation": raw}
        return normalize_gazebo_system_observation(record), raw

    def _verify(self, mission_id: str, trace_id: str, action_id: str, expected: Mapping[str, str]) -> tuple[dict[str, Any], dict[str, Any], Any]:
        observation, raw = self._observation(mission_id, action_id)
        request = self._request(mission_id, trace_id, "verification.verify", action_id=action_id)
        request.update({"verifier_id": "exact-state-verifier", "expected_state": dict(expected), "observation_refs": [dict(observation.reference)], "verification_profile_version": "sim-exact-match-v1"})
        validate_contract_message(request)
        return VerificationBackend().verify(request, [observation]), raw, observation

    def execute(self) -> dict[str, Any]:
        started = time.monotonic(); self.execution_started_at = datetime.now(timezone.utc); mission_id, trace_id = str(uuid.uuid4()), str(uuid.uuid4())
        mission_request = self._request(mission_id, trace_id, "mission.execute"); validate_contract_message(mission_request)
        transitions = [{"from": "created", "to": "ready"}, {"from": "ready", "to": "executing"}]
        steps: list[dict[str, Any]] = []
        source, destination = self.scenario["regions"]["source"], self.scenario["regions"]["destination"]
        try:
            if select_profile("system").integrated_world != "gazebo_harmonic": raise RuntimeError("system profile lost Gazebo authority")
            self.lifecycle["startup_attempted"] = True; self.world.start()
            if not (self.world.bootstrap_localization() and self.world.ready): raise RuntimeError("Gazebo system profile unavailable")
            nav = NavigationBackend(self.world)
            for label, region in (("source_navigation", source), ("destination_navigation", destination)):
                action_id = str(uuid.uuid4()); request = self._request(mission_id, trace_id, "navigation.execute", action_id=action_id)
                request.update({"robot_id": "amr-sim-001", "destination_id": region["id"], "speed_profile_id": "sim-safe-v1"})
                result = nav.execute(request); steps.append({"name": label, "request": request, "result": result})
                if result["result"] != "success": raise RuntimeError(f"{label} failed")
                if label == "source_navigation":
                    verification, observed, normalized = self._verify(mission_id, trace_id, action_id, self.scenario["initial_state"]); steps.append({"name": "source_verification", "expected_state": dict(self.scenario["initial_state"]), "observation": observed, "result": verification})
                    if verification.get("verdict") != "pass": raise RuntimeError("source verification failed")
            vla_action = str(uuid.uuid4()); vla_request = self._request(mission_id, trace_id, "vla.execute", action_id=vla_action)
            vla_request.update({"robot_id": "manipulator-sim-001", "task_id": "place-brake-ecu", "policy_version": "sim008-gazebo-surrogate-v1", "workspace_profile_id": "sim008-workspace-v1", "observation_refs": [dict(normalized.reference)]})
            changed = self.world.apply_vla_surrogate(task_id=vla_request["task_id"], expected_from=self.scenario["initial_state"], expected_to={"part_id": "brake-ecu-b", "location_id": destination["id"]})
            vla_result = {"operation": "vla.execute", "message_type": "result", "schema_version": "1.0", "mission_id": mission_id, "request_id": vla_request["request_id"], "trace_id": trace_id, "action_id": vla_action, "timestamp": _timestamp(), "component_version": COMPONENT_VERSION, "source_kind": "mock", "status": "succeeded" if changed else "failed", "result": "success" if changed else "failure", "skill_outcome": "succeeded" if changed else "failed", "latency_ms": 1, "verifier_input_refs": [{"uri": f"urn:factory-evidence:sim008:{vla_action}", "sha256": hashlib.sha256(vla_action.encode()).hexdigest()}]}
            if not changed: vla_result["error"] = {"code": "GAZEBO_SURROGATE_FAILED", "message": "Gazebo-side surrogate did not apply declared state transition", "category": "EXECUTION_FAILED", "retryable": False}
            validate_contract_message(vla_result); steps.append({"name": "vla.execute", "request": vla_request, "result": vla_result})
            if not changed: raise RuntimeError("VLA surrogate failed")
            expected_final = {"part_id": "brake-ecu-b", "location_id": destination["id"]}
            final, observed, _ = self._verify(mission_id, trace_id, vla_action, expected_final); steps.append({"name": "final_verification", "expected_state": expected_final, "observation": observed, "result": final})
            if final.get("verdict") != "pass": raise RuntimeError("final verification failed")
            transitions.append({"from": "executing", "to": "completed"})
            mission = {"operation": "mission.execute", "message_type": "result", "schema_version": "1.0", "mission_id": mission_id, "request_id": mission_request["request_id"], "trace_id": trace_id, "timestamp": _timestamp(), "component_version": COMPONENT_VERSION, "source_kind": "mock", "status": "completed", "result": "success", "checkpoint_revision": 6, "outcome": "completed"}; validate_contract_message(mission)
        except Exception as exc:
            transitions.append({"from": "executing", "to": "failed"}); mission = {"operation": "mission.execute", "message_type": "result", "schema_version": "1.0", "mission_id": mission_id, "request_id": mission_request["request_id"], "trace_id": trace_id, "timestamp": _timestamp(), "component_version": COMPONENT_VERSION, "source_kind": "mock", "status": "failed", "result": "failure", "checkpoint_revision": len(steps), "outcome": "failed", "error": {"code": "SYSTEM_E2E_FAILED", "message": str(exc), "category": "EXECUTION_FAILED", "retryable": False}}; validate_contract_message(mission)
        finally:
            self.lifecycle["cleanup_complete"] = self.world.close()
        return {"mission": mission, "mission_request": mission_request, "transitions": transitions, "steps": steps, "lifecycle": self.lifecycle, "duration_ms": round((time.monotonic() - started) * 1000, 3)}


def scenario_identity(scenario: Mapping[str, Any]) -> dict[str, str]:
    world = ROOT / str(scenario["world"])
    return {"scenario_sha256": canonical_sha256(dict(scenario)), "world_sha256": _hash(world), "config_sha256": _hash(SCENARIO_PATH), "world": str(scenario["world"])}
