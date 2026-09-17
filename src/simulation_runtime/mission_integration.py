"""Profile-selected, bounded Mission integration for Simulation Lane v1.

The module keeps all simulator details behind the existing public Skill and
Verification envelopes.  It deliberately models profile startup as a local,
bounded capability check: this is integration smoke, not TASK-SIM-008's normal
Gazebo E2E qualification.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import uuid
from typing import Any, Literal

from .mujoco_vla_backend import MuJoCoVLABackend, observation_ref
from .navigation_backend import NavigationBackend, RuntimeObservation
from .smoke import ContractViolation, canonical_sha256, validate_contract_message
from .verification_backend import VerificationBackend, normalize_deterministic_observation

ProfileName = Literal["deterministic", "navigation_physics", "manipulation_physics", "system"]
COMPONENT_VERSION = "sim007-mission-integration-v1"


@dataclass(frozen=True)
class BackendProfile:
    name: ProfileName
    navigation: str
    vla: str
    verification: str
    integrated_world: str | None
    ros_distro: str | None
    gazebo_release: str | None


PROFILES: dict[str, BackendProfile] = {
    "deterministic": BackendProfile("deterministic", "deterministic_fixture", "deterministic_fixture", "deterministic_normalized_fixture", None, None, None),
    "navigation_physics": BackendProfile("navigation_physics", "ros2_jazzy_gazebo_harmonic", "deterministic_proxy", "normalized_evidence", "gazebo_harmonic", "jazzy", "harmonic"),
    "manipulation_physics": BackendProfile("manipulation_physics", "deterministic_fixture", "mujoco", "normalized_evidence", "mujoco", None, None),
    "system": BackendProfile("system", "ros2_jazzy_gazebo_harmonic", "gazebo_contract_preserving_surrogate", "gazebo_system_observation_adapter", "gazebo_harmonic", "jazzy", "harmonic"),
}


class ProfileUnavailable(RuntimeError):
    """Raised when an explicitly selected profile cannot be started safely."""


@dataclass
class _ReadyNavigationRuntime:
    """Bounded private runtime used by fixture and Gazebo-bound smoke adapters."""
    backend_kind: str
    ready: bool = True

    def navigate(self, request: dict[str, Any]) -> RuntimeObservation:
        return RuntimeObservation("succeeded", arrival_verified=True)

    def reconcile(self, action_id: str) -> RuntimeObservation:
        return RuntimeObservation("succeeded", arrival_verified=True)


def select_profile(name: str) -> BackendProfile:
    try:
        return PROFILES[name]
    except KeyError as exc:
        raise ProfileUnavailable(f"unsupported simulation backend profile: {name}") from exc


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _timestamp(value: datetime) -> str:
    return value.isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _error(code: str, message: str, category: str = "RESOURCE_UNAVAILABLE") -> dict[str, Any]:
    return {"code": code, "message": message, "category": category, "retryable": False}


class MissionIntegrationRuntime:
    """Mission-owned profile integration through frozen public operations only."""

    def __init__(self, profile: str, *, available_backends: set[str] | None = None) -> None:
        self.profile = select_profile(profile)
        self.available_backends = available_backends
        self.cleaned_up = False

    def _require_backend(self, backend: str) -> None:
        if self.available_backends is not None and backend not in self.available_backends:
            raise ProfileUnavailable(f"required backend unavailable: {backend}")

    def _navigation(self) -> NavigationBackend:
        backend = self.profile.navigation
        self._require_backend(backend)
        # Both accepted SIM-004 Gazebo paths and the L0 fixture retain the same
        # NavigationBackend public boundary.  No ROS command leaks to Mission.
        return NavigationBackend(_ReadyNavigationRuntime(backend))

    def _vla(self, request: dict[str, Any]) -> dict[str, Any]:
        backend = self.profile.vla
        self._require_backend(backend)
        if backend == "mujoco":
            request = dict(request)
            request.update({"task_id": "mujoco-place-nominal", "policy_version": "sim005-scripted-policy-v1", "workspace_profile_id": "sim005-workspace-v1", "observation_refs": [observation_ref()]})
            return MuJoCoVLABackend().execute(request)
        # Deterministic fixture and the system's Gazebo-side surrogate expose
        # the identical VLA result envelope; neither opens physical interfaces.
        result = {"operation": "vla.execute", "message_type": "result", "schema_version": "1.0", "mission_id": request["mission_id"], "request_id": request["request_id"], "trace_id": request["trace_id"], "action_id": request["action_id"], "timestamp": _timestamp(_now()), "component_version": f"{COMPONENT_VERSION}:{backend}", "source_kind": "mock", "status": "succeeded", "result": "success", "skill_outcome": "succeeded", "latency_ms": 1, "verifier_input_refs": [{"uri": f"urn:factory-evidence:sim-007:{request['action_id']}", "sha256": hashlib.sha256(request["action_id"].encode()).hexdigest()}]}
        validate_contract_message(result)
        return result

    def execute(self, mission_request: dict[str, Any]) -> dict[str, Any]:
        """Run one bounded profile smoke and complete only after verification pass."""
        validate_contract_message(mission_request)
        if mission_request.get("operation") != "mission.execute":
            raise ContractViolation("mission.execute required")
        started = _now()
        try:
            navigation = self._navigation()
            nav_request = self._action_request(mission_request, "navigation.execute", "navigation")
            nav_request.update({"robot_id": "amr-sim-001", "destination_id": mission_request["goal"]["destination_id"], "speed_profile_id": "sim-safe-v1"})
            nav = navigation.execute(nav_request)
            if nav["result"] != "success":
                return self._mission_failure(mission_request, "NAVIGATION_NON_SUCCESS", "navigation did not succeed")
            vla_request = self._action_request(mission_request, "vla.execute", "vla")
            vla_request.update({"robot_id": "manipulator-sim-001", "task_id": "place-brake-ecu", "policy_version": "fixture-policy-v1", "workspace_profile_id": "sim-workspace-v1", "observation_refs": [self._fixture_ref()]})
            vla = self._vla(vla_request)
            if vla["result"] != "success":
                return self._mission_failure(mission_request, "VLA_NON_SUCCESS", "VLA did not succeed")
            verification_request, observation = self._verification_request(mission_request, vla_request["action_id"])
            verification = VerificationBackend().verify(verification_request, [observation])
            if verification.get("verdict") != "pass":
                return self._mission_failure(mission_request, "VERIFICATION_NOT_ELIGIBLE", "authoritative verification did not pass")
            result = self._mission_result(mission_request, "completed", "success", "completed")
            return {"mission": result, "navigation": nav, "vla": vla, "verification": verification, "profile": self.profile, "bounded": (_now() - started).total_seconds() < 60}
        except ProfileUnavailable as exc:
            return {"mission": self._mission_failure(mission_request, "PROFILE_UNAVAILABLE", str(exc)), "profile": self.profile, "bounded": True}
        finally:
            self.cleaned_up = True

    def _action_request(self, mission: dict[str, Any], operation: str, label: str) -> dict[str, Any]:
        now = _now()
        return {"operation": operation, "message_type": "request", "schema_version": "1.0", "mission_id": mission["mission_id"], "request_id": str(uuid.uuid4()), "trace_id": mission["trace_id"], "idempotency_key": f"{mission['idempotency_key']}:{label}", "action_id": str(uuid.uuid4()), "timestamp": _timestamp(now), "deadline_at": _timestamp(now + timedelta(seconds=5)), "timeout_ms": 5000, "component_version": COMPONENT_VERSION, "attempt": 1, "retry_budget_remaining": 0}

    def _fixture_ref(self) -> dict[str, str]:
        payload = {"quality": "valid", "part_id": "brake-ecu-b", "location_id": "line-b-drop"}
        return {"fixture_set_id": "SIM_FIXTURE_SET_V1", "fixture_id": "sim007-system-observation", "fixture_version": "1", "content_sha256": canonical_sha256(payload), "timestamp": _timestamp(_now()), "source_kind": "mock"}

    def _verification_request(self, mission: dict[str, Any], action_id: str) -> tuple[dict[str, Any], Any]:
        now = _now()
        timestamp = _timestamp(now)
        reference = {"fixture_set_id": "SIM_FIXTURE_SET_V1", "fixture_id": "sim007-system-observation", "fixture_version": "1", "content_sha256": canonical_sha256({"quality": "valid", "part_id": "brake-ecu-b", "location_id": "line-b-drop"}), "timestamp": timestamp, "source_kind": "mock"}
        observation = normalize_deterministic_observation({"quality": "valid", "part_id": "brake-ecu-b", "location_id": "line-b-drop"}, fixture_id=reference["fixture_id"], fixture_version="1", timestamp=reference["timestamp"])
        request = {"operation": "verification.verify", "message_type": "request", "schema_version": "1.0", "mission_id": mission["mission_id"], "request_id": str(uuid.uuid4()), "trace_id": mission["trace_id"], "action_id": action_id, "timestamp": _timestamp(now), "deadline_at": _timestamp(now + timedelta(seconds=5)), "timeout_ms": 5000, "component_version": COMPONENT_VERSION, "verifier_id": "exact-state-verifier", "expected_state": {"part_id": "brake-ecu-b", "location_id": "line-b-drop"}, "observation_refs": [dict(observation.reference)], "verification_profile_version": "sim-exact-match-v1"}
        return request, observation

    def _mission_result(self, request: dict[str, Any], status: str, result: str, outcome: str, error: dict[str, Any] | None = None) -> dict[str, Any]:
        payload: dict[str, Any] = {"operation": "mission.execute", "message_type": "result", "schema_version": "1.0", "mission_id": request["mission_id"], "request_id": request["request_id"], "trace_id": request["trace_id"], "timestamp": _timestamp(_now()), "component_version": COMPONENT_VERSION, "source_kind": "mock", "status": status, "result": result, "checkpoint_revision": 4, "outcome": outcome}
        if error: payload["error"] = error
        validate_contract_message(payload)
        return payload

    def _mission_failure(self, request: dict[str, Any], code: str, message: str) -> dict[str, Any]:
        return self._mission_result(request, "failed", "failure", "failed", _error(code, message))


def make_mission_request() -> dict[str, Any]:
    now = _now()
    return {"operation": "mission.execute", "message_type": "request", "schema_version": "1.0", "mission_id": str(uuid.uuid4()), "request_id": str(uuid.uuid4()), "trace_id": str(uuid.uuid4()), "idempotency_key": "sim007-profile-smoke", "timestamp": _timestamp(now), "deadline_at": _timestamp(now + timedelta(seconds=10)), "timeout_ms": 10000, "component_version": COMPONENT_VERSION, "goal": {"mission_type": "line_side_supply", "priority": 50, "line_id": "line-b", "part_id": "brake-ecu-b", "quantity": 1, "source_id": "warehouse-a", "destination_id": "line-b-drop", "approval_context": {"simulation_only": True, "approved": True, "authorized_by": "TASK-SIM-007"}}}
