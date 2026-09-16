"""Contract-only Navigation Skill adapter for the SIM-004 proxy Gazebo world.

The adapter intentionally accepts semantic destinations only.  It has no
hardware transport and makes ROS/Gazebo/Nav2 details private configuration.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .smoke import ContractViolation, validate_contract_message

ROOT = Path(__file__).resolve().parents[2]
COMPONENT_VERSION = "sim004-navigation-backend-v1"
DESTINATIONS = {"line-b-drop", "blocked-bay"}
SPEED_PROFILES = {"sim-safe-v1"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _error(code: str, message: str, category: str, retryable: bool = False) -> dict[str, Any]:
    return {"code": code, "message": message, "category": category, "retryable": retryable}


@dataclass
class NavigationBackend:
    """A bounded Nav2-facing proxy that preserves public contract identities."""

    ready: bool = True
    records: dict[str, dict[str, Any]] = field(default_factory=dict)

    def execute(self, request: dict[str, Any], *, behavior: str = "success") -> dict[str, Any]:
        """Execute one allowlisted semantic navigation request without exposing ROS APIs."""
        try:
            validate_contract_message(request)
        except ContractViolation as exc:
            return self._failure_from_request(request, "INVALID_NAVIGATION_REQUEST", str(exc), "VALIDATION")
        if request.get("operation") != "navigation.execute":
            return self._failure_from_request(request, "INVALID_OPERATION", "navigation.execute required", "VALIDATION")
        if request["destination_id"] not in DESTINATIONS or request["speed_profile_id"] not in SPEED_PROFILES:
            return self._failure_from_request(request, "INVALID_NAVIGATION_GOAL", "destination or speed profile is not allowlisted", "VALIDATION")
        if not self.ready:
            return self._failure_from_request(request, "NAVIGATION_UNAVAILABLE", "Nav2 lifecycle is not ready", "RESOURCE_UNAVAILABLE")
        action_id = request["action_id"]
        if behavior == "success":
            result = self._result(request, "succeeded", "success", arrival={"destination_id": request["destination_id"], "verified": True})
            self.records[action_id] = {"observed_status": "succeeded", "result": result}
        elif behavior in {"blocked", "aborted"}:
            result = self._failure_from_request(request, "NAVIGATION_ABORTED", "proxy world route is blocked or aborted", "EXECUTION_FAILED")
            self.records[action_id] = {"observed_status": "failed", "result": result}
        elif behavior == "timeout":
            result = self._result(request, "unknown", "pending", error=_error("NAVIGATION_TIMEOUT", "execution bound elapsed before authoritative outcome", "DEPENDENCY_TIMEOUT", True))
            self.records[action_id] = {"observed_status": "succeeded", "result": result}
        else:
            return self._failure_from_request(request, "INVALID_BEHAVIOR", "unsupported simulation behavior", "VALIDATION")
        validate_contract_message(result)
        return result

    def action_status_get(self, request: dict[str, Any]) -> dict[str, Any]:
        """Read authoritative simulated status; this is the only reconciliation path."""
        try:
            validate_contract_message(request)
        except ContractViolation as exc:
            return self._failure_from_request(request, "INVALID_STATUS_REQUEST", str(exc), "VALIDATION", operation="action_status.get")
        if request.get("operation") != "action_status.get" or request["action_id"] not in self.records:
            return self._failure_from_request(request, "ACTION_NOT_FOUND", "no authoritative action record", "RESOURCE_UNAVAILABLE", operation="action_status.get")
        observed = self.records[request["action_id"]]["observed_status"]
        return self._result(request, "succeeded", "success", operation="action_status.get", observed_status=observed)

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
        # Invalid input may lack a schema-valid envelope; return the closed semantic result when possible.
        required = {"mission_id", "request_id", "trace_id", "action_id"}
        if not required <= request.keys():
            raise ContractViolation(f"{code}: {message}")
        return self._result(request, "failed", "failure", operation=operation, error=_error(code, message, category))


def provenance() -> dict[str, Any]:
    """Return actual immutable task-owned asset identities for generated evidence."""
    paths = [
        "configs/simulation/sim004_navigation_proxy.yaml",
        "data/simulation/sim004_navigation_proxy_world.sdf",
        "scripts/run_simulation_navigation.py",
        "src/simulation_runtime/navigation_backend.py",
    ]
    return {"baseline_id": "SIM_BASELINE_V1", "proxy_model": "simulation_proxy_mobile_base", "physical_target": False,
            "assets": [{"path": path, "sha256": _sha256(ROOT / path)} for path in paths]}
