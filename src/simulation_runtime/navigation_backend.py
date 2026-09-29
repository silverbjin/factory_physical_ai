"""Navigation Skill contract adapter for a Gazebo/Nav2 simulation runtime.

This module deliberately contains no Gazebo, ROS, or Nav2 command handling.
Those details are supplied by the bounded runtime runner; the adapter accepts
only its authoritative observations and exposes the frozen Navigation Skill
contract to callers.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol

from .smoke import ContractViolation, validate_contract_message

ROOT = Path(__file__).resolve().parents[2]
COMPONENT_VERSION = "sim004-navigation-backend-v2"
# ``warehouse-a`` is the semantic source region used by the bounded SIM-008
# supply mission.  It remains a destination identifier here--never a raw pose.
DESTINATIONS = {"warehouse-a", "line-b-drop", "blocked-bay"}
SPEED_PROFILES = {"sim-safe-v1"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _error(code: str, message: str, category: str, retryable: bool = False) -> dict[str, Any]:
    return {"code": code, "message": message, "category": category, "retryable": retryable}


@dataclass(frozen=True)
class RuntimeObservation:
    """An authoritative result from the private Nav2-facing runtime."""

    observed_status: str
    arrival_verified: bool = False
    error_code: str = "NAVIGATION_FAILED"
    error_message: str = "Nav2 reported a non-success outcome"
    error_category: str = "EXECUTION_FAILED"
    retryable: bool = False


class NavigationRuntime(Protocol):
    """Private runtime boundary; implementations may use ROS actions only here."""

    @property
    def ready(self) -> bool: ...

    def navigate(self, request: dict[str, Any]) -> RuntimeObservation: ...

    def reconcile(self, action_id: str) -> RuntimeObservation: ...


@dataclass
class NavigationBackend:
    """Contract adapter; execution is impossible without an injected runtime."""

    runtime: NavigationRuntime | None = None
    records: dict[str, RuntimeObservation] = field(default_factory=dict)

    def execute(self, request: dict[str, Any]) -> dict[str, Any]:
        try:
            validate_contract_message(request)
        except ContractViolation as exc:
            return self._failure_from_request(request, "INVALID_NAVIGATION_REQUEST", str(exc), "VALIDATION")
        if request.get("operation") != "navigation.execute":
            return self._failure_from_request(request, "INVALID_OPERATION", "navigation.execute required", "VALIDATION")
        if request["destination_id"] not in DESTINATIONS or request["speed_profile_id"] not in SPEED_PROFILES:
            return self._failure_from_request(request, "INVALID_NAVIGATION_GOAL", "destination or speed profile is not allowlisted", "VALIDATION")
        if self.runtime is None or not self.runtime.ready:
            return self._failure_from_request(request, "NAVIGATION_UNAVAILABLE", "Nav2 lifecycle is not ready", "RESOURCE_UNAVAILABLE")

        observation = self.runtime.navigate(request)
        self.records[request["action_id"]] = observation
        if observation.observed_status == "succeeded" and observation.arrival_verified:
            result = self._result(request, "succeeded", "success", arrival={"destination_id": request["destination_id"], "verified": True})
        elif observation.observed_status == "unknown":
            result = self._result(request, "unknown", "pending", error=_error(observation.error_code, observation.error_message, "DEPENDENCY_TIMEOUT", True))
        else:
            result = self._failure_from_request(request, observation.error_code, observation.error_message, observation.error_category)
        validate_contract_message(result)
        return result

    def action_status_get(self, request: dict[str, Any]) -> dict[str, Any]:
        try:
            validate_contract_message(request)
        except ContractViolation as exc:
            return self._failure_from_request(request, "INVALID_STATUS_REQUEST", str(exc), "VALIDATION", operation="action_status.get")
        action_id = request.get("action_id")
        if request.get("operation") != "action_status.get" or action_id not in self.records:
            return self._failure_from_request(request, "ACTION_NOT_FOUND", "no authoritative action record", "RESOURCE_UNAVAILABLE", operation="action_status.get")
        observation = self.runtime.reconcile(action_id) if self.runtime is not None else self.records[action_id]
        self.records[action_id] = observation
        return self._result(request, "succeeded", "success", operation="action_status.get", observed_status=observation.observed_status)

    def _result(self, request: dict[str, Any], status: str, result: str, *, operation: str | None = None, **extra: Any) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "operation": operation or request["operation"], "message_type": "result", "schema_version": "1.0",
            "mission_id": request["mission_id"], "request_id": request["request_id"], "trace_id": request["trace_id"],
            "action_id": request["action_id"], "timestamp": _now(), "component_version": COMPONENT_VERSION,
            "source_kind": "mock", "status": status, "result": result,
            "evidence_refs": [{"uri": f"urn:factory-evidence:sim-004:{request['action_id']}", "sha256": hashlib.sha256(request["action_id"].encode()).hexdigest()}],
        }
        if operation == "action_status.get":
            payload["observed_at"] = _now()
        payload.update(extra)
        return payload

    def _failure_from_request(self, request: dict[str, Any], code: str, message: str, category: str, operation: str | None = None) -> dict[str, Any]:
        required = {"mission_id", "request_id", "trace_id", "action_id"}
        if not required <= request.keys():
            raise ContractViolation(f"{code}: {message}")
        return self._result(request, "failed", "failure", operation=operation, error=_error(code, message, category))


def provenance() -> dict[str, Any]:
    paths = [
        "configs/simulation/sim004_navigation_proxy.yaml",
        "data/simulation/sim004_navigation_proxy_world.sdf",
        "scripts/run_simulation_navigation.py",
        "src/simulation_runtime/navigation_backend.py",
    ]
    return {"baseline_id": "SIM_BASELINE_V1", "proxy_model": "simulation_proxy_mobile_base", "physical_target": False,
            "assets": [{"path": path, "sha256": _sha256(ROOT / path)} for path in paths]}
