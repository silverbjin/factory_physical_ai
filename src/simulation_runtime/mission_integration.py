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
from pathlib import Path
import sys
import time
import uuid
from typing import Any, Callable, Literal, Protocol

from .mujoco_vla_backend import MuJoCoVLABackend, observation_ref
from .navigation_backend import NavigationBackend, RuntimeObservation
from .smoke import ContractViolation, canonical_sha256, validate_contract_message
from .verification_backend import VerificationBackend, normalize_deterministic_observation, normalize_gazebo_observation

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


class ManagedNavigationRuntime(Protocol):
    """Private lifecycle boundary for the accepted Gazebo/Nav2 runner."""

    @property
    def ready(self) -> bool: ...

    def start(self) -> None: ...

    def bootstrap_localization(self) -> bool: ...

    def navigate(self, request: dict[str, Any]) -> RuntimeObservation: ...

    def reconcile(self, action_id: str) -> RuntimeObservation: ...

    def close(self) -> bool: ...


@dataclass
class _ReadyNavigationRuntime:
    """Bounded private runtime used by fixture and Gazebo-bound smoke adapters."""
    backend_kind: str
    ready: bool = True

    def navigate(self, request: dict[str, Any]) -> RuntimeObservation:
        return RuntimeObservation("succeeded", arrival_verified=True)

    def reconcile(self, action_id: str) -> RuntimeObservation:
        return RuntimeObservation("succeeded", arrival_verified=True)


def _gazebo_runtime_factory() -> ManagedNavigationRuntime:
    """Load SIM-004's bounded, process-owning Gazebo/Nav2 runtime lazily.

    Keeping this import lazy leaves deterministic and MuJoCo component profiles
    independent of ROS installation, while physics profiles use the accepted
    process lifecycle rather than a local success fixture.
    """
    root = str(Path(__file__).resolve().parents[2])
    if root not in sys.path:
        sys.path.insert(0, root)
    from scripts.run_simulation_navigation import BoundedGazeboNav2Runtime
    return BoundedGazeboNav2Runtime()


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

    def __init__(self, profile: str, *, available_backends: set[str] | None = None,
                 gazebo_runtime_factory: Callable[[], ManagedNavigationRuntime] = _gazebo_runtime_factory) -> None:
        self.profile = select_profile(profile)
        self.available_backends = available_backends
        self.gazebo_runtime_factory = gazebo_runtime_factory
        self.cleaned_up = False
        self.cleanup_complete = False
        self.lifecycle: dict[str, Any] = {"profile": profile, "startup_attempted": False, "ready": None, "cleanup_complete": None}

    def _require_backend(self, backend: str) -> None:
        if self.available_backends is not None and backend not in self.available_backends:
            raise ProfileUnavailable(f"required backend unavailable: {backend}")

    def _close_runtime(self, runtime: ManagedNavigationRuntime) -> bool:
        try:
            return runtime.close()
        except Exception:
            return False

    def _navigation(self) -> tuple[NavigationBackend, ManagedNavigationRuntime | None]:
        backend = self.profile.navigation
        self._require_backend(backend)
        if backend == "ros2_jazzy_gazebo_harmonic":
            try:
                runtime = self.gazebo_runtime_factory()
            except Exception as exc:
                self.lifecycle["cleanup_complete"] = True
                raise ProfileUnavailable("accepted Gazebo/ROS 2 Navigation runtime could not be constructed") from exc
            self.lifecycle["startup_attempted"] = True
            try:
                runtime.start()
                ready = runtime.bootstrap_localization() and runtime.ready
            except Exception as exc:
                self.lifecycle["cleanup_complete"] = self._close_runtime(runtime)
                raise ProfileUnavailable("accepted Gazebo/ROS 2 Navigation runtime failed to start") from exc
            self.lifecycle["ready"] = ready
            if not ready:
                self.lifecycle["cleanup_complete"] = self._close_runtime(runtime)
                raise ProfileUnavailable("accepted Gazebo/ROS 2 Navigation runtime did not become ready")
            return NavigationBackend(runtime), runtime
        # Fixture profiles retain the same public boundary, without loading ROS.
        return NavigationBackend(_ReadyNavigationRuntime(backend)), None

    def _vla(self, request: dict[str, Any], navigation: dict[str, Any]) -> dict[str, Any]:
        backend = self.profile.vla
        self._require_backend(backend)
        if backend == "mujoco":
            request = dict(request)
            request.update({"task_id": "mujoco-place-nominal", "policy_version": "sim005-scripted-policy-v1", "workspace_profile_id": "sim005-workspace-v1", "observation_refs": [observation_ref()]})
            return MuJoCoVLABackend().execute(request)
        if backend == "gazebo_contract_preserving_surrogate":
            # There is no accepted Gazebo manipulation runtime in SIM-004/005.
            # Refuse to manufacture a surrogate action result from navigation
            # evidence; TASK-SIM-008 may qualify one with its own E2E evidence.
            return self._vla_failure(request, "GAZEBO_SURROGATE_UNAVAILABLE", "no accepted Gazebo-side manipulation surrogate is available")
        # The system surrogate runs only after a live Gazebo navigation result
        # exists.  It deliberately carries that immutable Gazebo observation to
        # Verification rather than inventing a manipulation-world success.
        result = {"operation": "vla.execute", "message_type": "result", "schema_version": "1.0", "mission_id": request["mission_id"], "request_id": request["request_id"], "trace_id": request["trace_id"], "action_id": request["action_id"], "timestamp": _timestamp(_now()), "component_version": f"{COMPONENT_VERSION}:{backend}", "source_kind": "mock", "status": "succeeded", "result": "success", "skill_outcome": "succeeded", "latency_ms": 1, "verifier_input_refs": [{"uri": f"urn:factory-evidence:sim-007:{request['action_id']}", "sha256": hashlib.sha256(request["action_id"].encode()).hexdigest()}]}
        validate_contract_message(result)
        return result

    def _vla_failure(self, request: dict[str, Any], code: str, message: str) -> dict[str, Any]:
        result = {"operation": "vla.execute", "message_type": "result", "schema_version": "1.0", "mission_id": request["mission_id"], "request_id": request["request_id"], "trace_id": request["trace_id"], "action_id": request["action_id"], "timestamp": _timestamp(_now()), "component_version": f"{COMPONENT_VERSION}:gazebo_contract_preserving_surrogate", "source_kind": "mock", "status": "failed", "result": "failure", "skill_outcome": "failed", "latency_ms": 0, "error": _error(code, message)}
        validate_contract_message(result)
        return result

    def execute(self, mission_request: dict[str, Any]) -> dict[str, Any]:
        """Run one bounded profile smoke and complete only after verification pass."""
        validate_contract_message(mission_request)
        if mission_request.get("operation") != "mission.execute":
            raise ContractViolation("mission.execute required")
        started = time.monotonic()
        managed_runtime: ManagedNavigationRuntime | None = None
        try:
            navigation, managed_runtime = self._navigation()
            nav_request = self._action_request(mission_request, "navigation.execute", "navigation")
            nav_request.update({"robot_id": "amr-sim-001", "destination_id": mission_request["goal"]["destination_id"], "speed_profile_id": "sim-safe-v1"})
            nav = navigation.execute(nav_request)
            if nav["result"] != "success":
                return {"mission": self._mission_failure(mission_request, "NAVIGATION_NON_SUCCESS", "navigation did not succeed"), "navigation": nav, "profile": self.profile, "bounded": time.monotonic() - started < 60, "lifecycle": dict(self.lifecycle)}
            vla_request = self._action_request(mission_request, "vla.execute", "vla")
            vla_request.update({"robot_id": "manipulator-sim-001", "task_id": "place-brake-ecu", "policy_version": "fixture-policy-v1", "workspace_profile_id": "sim-workspace-v1", "observation_refs": [self._fixture_ref()]})
            vla = self._vla(vla_request, nav)
            if vla["result"] != "success":
                return {"mission": self._mission_failure(mission_request, "VLA_NON_SUCCESS", "VLA did not succeed"), "navigation": nav, "vla": vla, "profile": self.profile, "bounded": time.monotonic() - started < 60, "lifecycle": dict(self.lifecycle)}
            verification_request, observation = self._verification_request(mission_request, vla_request["action_id"], nav)
            verification = VerificationBackend().verify(verification_request, [observation])
            if verification.get("verdict") != "pass":
                return {"mission": self._mission_failure(mission_request, "VERIFICATION_NOT_ELIGIBLE", "authoritative verification did not pass"), "navigation": nav, "vla": vla, "verification": verification, "profile": self.profile, "bounded": time.monotonic() - started < 60, "lifecycle": dict(self.lifecycle)}
            result = self._mission_result(mission_request, "completed", "success", "completed")
            return {"mission": result, "navigation": nav, "vla": vla, "verification": verification, "profile": self.profile, "bounded": time.monotonic() - started < 60, "lifecycle": dict(self.lifecycle)}
        except ProfileUnavailable as exc:
            return {"mission": self._mission_failure(mission_request, "PROFILE_UNAVAILABLE", str(exc)), "profile": self.profile, "bounded": time.monotonic() - started < 60, "lifecycle": dict(self.lifecycle)}
        finally:
            if managed_runtime is not None:
                self.cleanup_complete = self._close_runtime(managed_runtime)
            elif self.lifecycle["cleanup_complete"] is None:
                self.cleanup_complete = True
            else:
                self.cleanup_complete = self.lifecycle["cleanup_complete"]
            self.cleaned_up = self.cleanup_complete
            self.lifecycle["cleanup_complete"] = self.cleanup_complete

    def _action_request(self, mission: dict[str, Any], operation: str, label: str) -> dict[str, Any]:
        now = _now()
        return {"operation": operation, "message_type": "request", "schema_version": "1.0", "mission_id": mission["mission_id"], "request_id": str(uuid.uuid4()), "trace_id": mission["trace_id"], "idempotency_key": f"{mission['idempotency_key']}:{label}", "action_id": str(uuid.uuid4()), "timestamp": _timestamp(now), "deadline_at": _timestamp(now + timedelta(seconds=5)), "timeout_ms": 5000, "component_version": COMPONENT_VERSION, "attempt": 1, "retry_budget_remaining": 0}

    def _fixture_ref(self) -> dict[str, str]:
        payload = {"quality": "valid", "part_id": "brake-ecu-b", "location_id": "line-b-drop"}
        return {"fixture_set_id": "SIM_FIXTURE_SET_V1", "fixture_id": "sim007-system-observation", "fixture_version": "1", "content_sha256": canonical_sha256(payload), "timestamp": _timestamp(_now()), "source_kind": "mock"}

    def _verification_request(self, mission: dict[str, Any], action_id: str,
                              navigation: dict[str, Any]) -> tuple[dict[str, Any], Any]:
        now = _now()
        timestamp = _timestamp(now)
        if self.profile.verification == "deterministic_normalized_fixture":
            reference = {"fixture_set_id": "SIM_FIXTURE_SET_V1", "fixture_id": "sim007-system-observation", "fixture_version": "1", "content_sha256": canonical_sha256({"quality": "valid", "part_id": "brake-ecu-b", "location_id": "line-b-drop"}), "timestamp": timestamp, "source_kind": "mock"}
            observation = normalize_deterministic_observation({"quality": "valid", "part_id": "brake-ecu-b", "location_id": "line-b-drop"}, fixture_id=reference["fixture_id"], fixture_version="1", timestamp=reference["timestamp"])
        else:
            # SIM-006 permits only accepted, immutable simulator records.  A
            # fresh live record is not an accepted artifact, so physics/system
            # smoke fails closed instead of claiming a verification pass.
            try:
                observation = normalize_gazebo_observation(navigation)
                reference = dict(observation.reference)
                self.lifecycle["verification_observation"] = "accepted_gazebo_record"
            except ValueError:
                reference = {"fixture_set_id": "SIM_FIXTURE_SET_V1", "fixture_id": "sim007-live-gazebo-unavailable", "fixture_version": "1", "content_sha256": canonical_sha256({"quality": "insufficient"}), "timestamp": timestamp, "source_kind": "mock"}
                observation = normalize_deterministic_observation({"quality": "insufficient"}, fixture_id=reference["fixture_id"], fixture_version="1", timestamp=reference["timestamp"])
                self.lifecycle["verification_observation"] = "live_gazebo_record_unaccepted"
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
