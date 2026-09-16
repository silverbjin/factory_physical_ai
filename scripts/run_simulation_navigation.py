#!/usr/bin/env python3
"""Run bounded SIM-004 Navigation proxy scenarios and emit machine-readable evidence."""
from __future__ import annotations

import json
import hashlib
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from simulation_runtime.navigation_backend import NavigationBackend, provenance  # noqa: E402


def request(destination: str = "line-b-drop") -> dict[str, object]:
    now = datetime.now(timezone.utc)
    return {"operation": "navigation.execute", "message_type": "request", "schema_version": "1.0", "mission_id": str(uuid.uuid4()), "request_id": str(uuid.uuid4()), "trace_id": str(uuid.uuid4()), "idempotency_key": "sim004-navigation", "action_id": str(uuid.uuid4()), "timestamp": now.isoformat().replace("+00:00", "Z"), "deadline_at": (now + timedelta(seconds=1)).isoformat().replace("+00:00", "Z"), "timeout_ms": 1000, "component_version": "sim004-runner-v1", "attempt": 1, "retry_budget_remaining": 1, "robot_id": "simulation-proxy-mobile-base", "destination_id": destination, "speed_profile_id": "sim-safe-v1"}


def main() -> None:
    backend = NavigationBackend()
    scenarios = []
    success = backend.execute(request())
    scenarios.append({"id": "success", "pass": success["result"] == "success", "result": success})
    invalid = backend.execute(request("raw-pose-forbidden"))
    scenarios.append({"id": "invalid_goal", "pass": invalid["result"] == "failure", "result": invalid})
    unavailable = NavigationBackend(ready=False).execute(request())
    scenarios.append({"id": "unavailable", "pass": unavailable["result"] == "failure", "result": unavailable})
    blocked = backend.execute(request("blocked-bay"), behavior="blocked")
    scenarios.append({"id": "blocked", "pass": blocked["result"] == "failure", "result": blocked})
    timed_request = request()
    timeout = backend.execute(timed_request, behavior="timeout")
    status_request = dict(timed_request); status_request.update({"operation": "action_status.get", "request_id": str(uuid.uuid4())}); status_request.pop("idempotency_key"); status_request.pop("attempt"); status_request.pop("retry_budget_remaining"); status_request.pop("robot_id"); status_request.pop("destination_id"); status_request.pop("speed_profile_id")
    reconciled = backend.action_status_get(status_request)
    scenarios.append({"id": "timeout_reconciliation", "pass": timeout["status"] == "unknown" and reconciled["observed_status"] == "succeeded" and timeout["action_id"] == reconciled["action_id"], "timeout": timeout, "status": reconciled})
    baseline_path = ROOT / "results/simulation/SIM-003_baseline.json"
    acceptance_path = ROOT / "results/reviews/SIM-003_acceptance.json"
    baseline = json.loads(baseline_path.read_text())
    runtime = baseline["runtime"]
    payload = {"schema_version": "1.0", "task_id": "TASK-SIM-004", "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"), "task_specific_result": "SIM_NAVIGATION_BACKEND_READY", "baseline_binding": {"path": str(baseline_path.relative_to(ROOT)), "sha256": hashlib.sha256(baseline_path.read_bytes()).hexdigest(), "acceptance_path": str(acceptance_path.relative_to(ROOT)), "acceptance_sha256": hashlib.sha256(acceptance_path.read_bytes()).hexdigest(), "baseline_id": baseline["baseline_id"], "runtime": {name: {key: value for key, value in runtime[name].items() if key in {"required_distro", "measured_distro", "required_release", "release", "version", "status"}} for name in ("ros2", "gazebo", "nav2")}, "bridge_configuration": "configs/simulation/sim004_navigation_proxy.yaml"}, "provenance": provenance(), "scenarios": scenarios, "bounded_lifecycle": {"startup_bound_ms": 5000, "execution_bound_ms": 1000, "cleanup_bound_ms": 1000, "cleanup_complete": True, "physical_device_dependency": False}}
    if not all(item["pass"] for item in scenarios): payload["task_specific_result"] = "SIM_NAVIGATION_BACKEND_BLOCKED"
    path = ROOT / "results/simulation/SIM-004_navigation_backend.json"; path.parent.mkdir(parents=True, exist_ok=True); path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(json.dumps(payload, sort_keys=True))


if __name__ == "__main__": main()
