from __future__ import annotations

import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from simulation_runtime.navigation_backend import NavigationBackend, provenance  # noqa: E402
from simulation_runtime.smoke import validate_contract_message  # noqa: E402


def request(destination: str = "line-b-drop") -> dict[str, object]:
    now = datetime.now(timezone.utc)
    return {"operation": "navigation.execute", "message_type": "request", "schema_version": "1.0", "mission_id": str(uuid.uuid4()), "request_id": str(uuid.uuid4()), "trace_id": str(uuid.uuid4()), "idempotency_key": "test-navigation", "action_id": str(uuid.uuid4()), "timestamp": now.isoformat().replace("+00:00", "Z"), "deadline_at": (now + timedelta(seconds=1)).isoformat().replace("+00:00", "Z"), "timeout_ms": 1000, "component_version": "test", "attempt": 1, "retry_budget_remaining": 1, "robot_id": "simulation-proxy-mobile-base", "destination_id": destination, "speed_profile_id": "sim-safe-v1"}


def status_request(execute: dict[str, object]) -> dict[str, object]:
    return {key: execute[key] for key in ("schema_version", "mission_id", "trace_id", "timestamp", "deadline_at", "timeout_ms", "component_version", "action_id")} | {"operation": "action_status.get", "message_type": "request", "request_id": str(uuid.uuid4())}


def test_success_is_contract_valid_and_arrives_at_requested_destination() -> None:
    req = request(); result = NavigationBackend().execute(req)
    validate_contract_message(result)
    assert result["result"] == "success" and result["arrival"]["destination_id"] == req["destination_id"]


def test_invalid_unavailable_and_blocked_fail_closed() -> None:
    assert NavigationBackend().execute(request("not-allowlisted"))["result"] == "failure"
    assert NavigationBackend(ready=False).execute(request())["error"]["category"] == "RESOURCE_UNAVAILABLE"
    assert NavigationBackend().execute(request("blocked-bay"), behavior="blocked")["status"] == "failed"


def test_timeout_stays_unknown_until_authoritative_status_lookup() -> None:
    backend = NavigationBackend(); req = request(); timeout = backend.execute(req, behavior="timeout")
    lookup = backend.action_status_get(status_request(req))
    validate_contract_message(timeout); validate_contract_message(lookup)
    assert timeout["result"] == "pending" and timeout["status"] == "unknown"
    assert timeout["action_id"] == lookup["action_id"] == req["action_id"]
    assert lookup["observed_status"] == "succeeded"


def test_provenance_is_hashed_and_explicitly_nonphysical() -> None:
    info = provenance()
    assert info["baseline_id"] == "SIM_BASELINE_V1" and info["physical_target"] is False
    assert len(info["assets"]) == 4 and all(len(item["sha256"]) == 64 for item in info["assets"])
