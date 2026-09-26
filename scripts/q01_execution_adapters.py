"""Q01 wrappers around accepted simulation execution paths; never write predecessor Evidence."""
from __future__ import annotations

import hashlib
import json
import subprocess
import uuid
from pathlib import Path
from typing import Any
from collections.abc import Callable, Mapping

ROOT = Path(__file__).resolve().parents[1]


def gazebo_clock(runtime: Any, world_name: str) -> dict[str, Any]:
    """Obtain one structured Gazebo stats response in the runtime transport partition."""
    result = subprocess.run(
        ["gz", "topic", "-e", "-n", "1", "--json-output", "-t", f"/world/{world_name}/stats"],
        text=True, capture_output=True, timeout=5, check=False, env=runtime.environment,
    )
    if result.returncode:
        raise RuntimeError("Gazebo stats sidecar failed")
    return json.loads(result.stdout)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_sim005_qualification(task_id: str) -> dict[str, Any]:
    """Run one new Q01 envelope through the accepted MuJoCo backend path."""
    from scripts.run_simulation_mujoco_vla import request
    from simulation_runtime.mujoco_vla_backend import MuJoCoVLABackend, provenance

    request_data = request(task_id)
    backend = MuJoCoVLABackend()
    result = backend.execute(request_data)
    correlation = {field: request_data[field] for field in ("mission_id", "request_id", "trace_id", "action_id")}
    measurement = backend.measurement_for(request_data["mission_id"], request_data["action_id"])
    return {
        "qualification_run_id": f"q01-sim005-{task_id}-{uuid.uuid4()}",
        "new_run": True,
        "correlation_identity": correlation,
        "measurement": measurement,
        "provenance": provenance(),
        "semantic_outcome": {"result": result["result"], "status": result["status"], "error": result.get("error")},
    }


def _find_simulation_time(value: Any) -> Mapping[str, int] | None:
    if isinstance(value, Mapping):
        candidate = value.get("simulation_time")
        if isinstance(candidate, Mapping) and set(candidate) == {"sec", "nsec"}:
            return candidate
        for child in value.values():
            found = _find_simulation_time(child)
            if found is not None:
                return found
    if isinstance(value, list):
        for child in value:
            found = _find_simulation_time(child)
            if found is not None:
                return found
    return None


def run_sim008_qualification(executor: Callable[[], Mapping[str, Any]] | None = None) -> dict[str, Any]:
    """Wrap the accepted normal E2E execution without changing its semantics."""
    from simulation_runtime.normal_system_e2e import COMPONENT_VERSION, SCENARIO_PATH, load_scenario, scenario_identity

    scenario = load_scenario()
    if executor is None:
        from scripts.run_simulation_normal_system_e2e import GazeboSystemWorld
        from simulation_runtime.normal_system_e2e import NormalSystemE2E
        executor = lambda: NormalSystemE2E(GazeboSystemWorld(scenario), scenario).execute()
    outcome = executor()
    simulation_time = _find_simulation_time(outcome)
    if simulation_time is None:
        raise ValueError("MISSING_STRUCTURED_SIMULATION_TIME")
    mission = outcome.get("mission") if isinstance(outcome.get("mission"), Mapping) else {}
    lifecycle = outcome.get("lifecycle") if isinstance(outcome.get("lifecycle"), Mapping) else {}
    correlation = {field: mission.get(field) for field in ("mission_id", "request_id", "trace_id")}
    if not all(isinstance(value, str) and value for value in correlation.values()):
        raise ValueError("MISSING_RUN_LOCAL_CORRELATION")
    identity = scenario_identity(scenario)
    bridge_path = ROOT / "src/simulation_runtime/normal_system_e2e.py"
    system_identity = hashlib.sha256(json.dumps({"profile": scenario["profile"], "model": scenario["model"]}, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return {
        "qualification_run_id": "q01-sim008-normal-system-authority",
        "scenario_id": scenario["scenario_id"],
        "backend_id": "gazebo",
        "component_version": mission.get("component_version", COMPONENT_VERSION),
        "correlation_identity": correlation,
        "execution_authority": {
            "world_sha256": identity["world_sha256"],
            "system_sha256": system_identity,
            "bridge_sha256": sha256(bridge_path),
            "launch_sha256": identity["config_sha256"],
            "source_paths": {
                "world": identity["world"],
                "bridge_configuration": str(bridge_path.relative_to(ROOT)),
                "launch_run_configuration": str(SCENARIO_PATH.relative_to(ROOT)),
            },
        },
        "simulation_time": {
            "source": "gazebo_authoritative_observation",
            "seconds": simulation_time["sec"] + simulation_time["nsec"] / 1_000_000_000,
            "raw": dict(simulation_time),
        },
        "startup_attempted": lifecycle.get("startup_attempted"),
        "cleanup_complete": lifecycle.get("cleanup_complete"),
        "semantic_outcome": {field: mission[field] for field in ("result", "status", "error") if field in mission},
    }


def run_sim009_qualification(executor: Callable[[], Mapping[str, Any]] | None = None) -> dict[str, dict[str, Any]]:
    """Wrap the accepted failure suite and retain its exact scenario identities."""
    if executor is None:
        from simulation_runtime.failure_recovery import run_failure_suite
        executor = run_failure_suite
    suite = executor()
    rows = suite.get("scenarios")
    if not isinstance(rows, list):
        raise ValueError("MISSING_SIM009_SCENARIOS")
    records: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, Mapping) or not isinstance(row.get("id"), str):
            raise ValueError("INVALID_SCENARIO_ID")
        scenario_id = row["id"]
        if scenario_id in records:
            raise ValueError("DUPLICATE_SCENARIO_ID")
        records[scenario_id] = {
            "qualification_run_id": f"q01-sim009-{scenario_id}",
            "backend_id": row.get("backend"),
            "cleanup_complete": row.get("cleanup_complete"),
            "semantic_outcome": {"decision": row.get("decision"), "outcome_kind": row.get("outcome_kind")},
            "raw_result": row.get("result") or row.get("verification") or row.get("first_result"),
        }
    return records
