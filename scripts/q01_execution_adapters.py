"""Q01 wrappers around accepted simulation execution paths; never write predecessor Evidence."""
from __future__ import annotations

import hashlib
import json
import subprocess
import time
import uuid
from pathlib import Path
from typing import Any
from collections.abc import Callable, Mapping

ROOT = Path(__file__).resolve().parents[1]
_GAZEBO_STATS_TIMEOUT_SECONDS = 15
_SIM009_GAZEBO_STATS_ATTEMPTS = 2

_SIM004_SCENARIOS: Mapping[str, Mapping[str, object]] = {
    "success": {"qualification_run_id": "q01-sim004-success-time", "destination": "line-b-drop", "timeout_ms": 30_000},
    "blocked": {"qualification_run_id": "q01-sim004-blocked-time", "destination": "blocked-bay", "timeout_ms": 30_000},
    "timeout_reconciliation": {"qualification_run_id": "q01-sim004-timeout-reconciliation-time", "destination": "line-b-drop", "timeout_ms": 1},
}


def gazebo_clock(runtime: Any, world_name: str) -> dict[str, Any]:
    """Obtain one structured Gazebo stats response in the runtime transport partition."""
    try:
        result = subprocess.run(
            ["gz", "topic", "-e", "-n", "1", "--json-output", "-t", f"/world/{world_name}/stats"],
            text=True, capture_output=True, timeout=_GAZEBO_STATS_TIMEOUT_SECONDS,
            check=False, env=runtime.environment,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError("Gazebo stats sidecar timed out") from exc
    if result.returncode:
        raise RuntimeError("Gazebo stats sidecar failed")
    return json.loads(result.stdout)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_sim004_qualification(
    scenario_id: str,
    *,
    runtime_factory: Callable[[], Any] | None = None,
    clock_probe: Callable[[Any, str], Mapping[str, Any]] = gazebo_clock,
) -> dict[str, Any]:
    """Run one accepted SIM-004 scenario and retain only its new-run observations.

    This composes the bounded accepted Nav2 runtime with the existing Gazebo
    sidecar.  It deliberately returns raw execution facts: the Q01 collector,
    not this adapter, constructs the qualification subject.
    """
    if scenario_id not in _SIM004_SCENARIOS:
        raise ValueError("UNKNOWN_SIM004_QUALIFICATION_SCENARIO")
    from scripts.run_simulation_navigation import BoundedGazeboNav2Runtime, request, status_request
    from simulation_runtime.navigation_backend import NavigationBackend, provenance
    from simulation_runtime.provenance_qualification import read_gazebo_simulation_time

    spec = _SIM004_SCENARIOS[scenario_id]
    runtime = runtime_factory() if runtime_factory is not None else BoundedGazeboNav2Runtime()
    started = time.monotonic()
    outcome: dict[str, Any] = {"result": "failure", "status": "failed"}
    reconciliation: Mapping[str, Any] | None = None
    simulation_time: Mapping[str, Any] | None = None
    startup_ready = False
    execution_error: str | None = None
    try:
        runtime.start()
        startup_ready = runtime.bootstrap_localization()
        if not startup_ready:
            outcome = {"result": "failure", "status": "failed", "error": "LOCALIZATION_NOT_READY"}
        else:
            backend = NavigationBackend(runtime)
            operation = request(str(spec["destination"]), timeout_ms=int(spec["timeout_ms"]))
            outcome = backend.execute(operation)
            if scenario_id == "timeout_reconciliation":
                reconciliation = backend.action_status_get(status_request(operation))
        # This is a new runtime observation, never a value from predecessor Evidence.
        simulation_time = read_gazebo_simulation_time(json.dumps(clock_probe(runtime, "sim004_navigation_proxy_world")))
    except Exception as exc:  # Preserve failure for the collector/aggregator to fail closed.
        execution_error = f"{type(exc).__name__}: {exc}"
    finally:
        cleanup_complete = runtime.close()

    assets = {asset["path"]: asset["sha256"] for asset in provenance()["assets"]}
    semantic_outcome = {key: outcome[key] for key in ("result", "status", "error") if key in outcome}
    if reconciliation is not None:
        semantic_outcome["reconciliation"] = {
            key: reconciliation[key] for key in ("result", "status", "observed_status") if key in reconciliation
        }
    if execution_error is not None:
        semantic_outcome["execution_error"] = execution_error
    return {
        "qualification_run_id": spec["qualification_run_id"],
        "scenario_id": scenario_id,
        "simulation_time": simulation_time,
        "wall_time_ms": round((time.monotonic() - started) * 1000, 3),
        "world_sha256": sha256(Path(runtime.world_path)),
        "bridge_sha256": assets["configs/simulation/sim004_navigation_proxy.yaml"],
        "launch_sha256": assets["scripts/run_simulation_navigation.py"],
        "startup_ready": startup_ready,
        "cleanup_complete": cleanup_complete,
        "semantic_outcome": semantic_outcome,
    }


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
    controlled = executor is not None
    if executor is None:
        from simulation_runtime.failure_recovery import run_failure_suite
        executor = lambda: run_failure_suite(scenario_observer=_sim009_sidecar_observation)
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
        raw_result = row.get("result") or row.get("verification") or row.get("first_result")
        raw_result = raw_result if isinstance(raw_result, Mapping) else {}
        attempt = row.get("qualification_attempt")
        if not isinstance(attempt, Mapping) or not all(
            isinstance(attempt.get(field), str) and attempt[field]
            for field in ("qualification_run_id", "scenario_execution_id")
        ):
            if not controlled:
                raise ValueError("MISSING_SIM009_ATTEMPT_IDENTITY")
            attempt = {
                "qualification_run_id": f"q01-sim009-controlled-{scenario_id}",
                "scenario_execution_id": f"controlled-{scenario_id}",
            }
        correlation = {
            field: raw_result[field]
            for field in ("mission_id", "request_id", "trace_id", "action_id")
            if isinstance(raw_result.get(field), str) and raw_result[field]
        }
        semantic_outcome = {key: value for key, value in {
            "decision": row.get("decision"), "outcome_kind": row.get("outcome_kind"),
            "result": raw_result.get("result"), "status": raw_result.get("status"),
        }.items() if value is not None}
        for key in (
            "reconciliation", "retry_authorization", "retry_request", "retry_result",
            "retry_suppressed", "identity", "logical_side_effect_count", "recovery",
            "verification", "route", "mission",
        ):
            if key in row:
                semantic_outcome[key] = row[key]
        records[scenario_id] = {
            "qualification_run_id": attempt["qualification_run_id"],
            "scenario_id": scenario_id,
            "backend_id": row.get("backend"),
            "component_version": raw_result.get("component_version", "sim009-failure-suite-v1"),
            "correlation_identity": correlation,
            "execution_identity": dict(attempt),
            "cleanup_complete": row.get("cleanup_complete"),
            "semantic_outcome": semantic_outcome,
            "raw_result": raw_result,
            "run_local_provenance": row.get("qualification_observation"),
        }
    return records


def _sim009_sidecar_observation(
    scenario: Mapping[str, Any], row: Mapping[str, Any], runtime: Any,
) -> dict[str, Any] | None:
    """Capture only same-run simulator facts; an unavailable probe remains absent."""
    backend = scenario.get("backend")
    manifest = ROOT / "configs/simulation/sim009_failure_scenarios.json"
    if backend == "gazebo_navigation":
        if runtime is None:
            return None
        seconds = None
        for _attempt in range(_SIM009_GAZEBO_STATS_ATTEMPTS):
            try:
                stats = gazebo_clock(runtime, "sim004_navigation_proxy_world")
                sim_time = stats["simTime"]
                seconds = int(sim_time["sec"]) + int(sim_time.get("nsec", 0)) / 1_000_000_000
            except (KeyError, TypeError, ValueError, RuntimeError):
                continue
            break
        if seconds is None:
            return None
        world = ROOT / "data/simulation/sim004_navigation_proxy_world.sdf"
        return {
            "simulation_time": {"source": "gz_stats", "seconds": seconds},
            "configuration_sha256": sha256(manifest),
            "world_model_sha256": sha256(world),
            "source_paths": {"configuration": str(manifest.relative_to(ROOT)), "world_model": str(world.relative_to(ROOT))},
        }
    if backend != "mujoco":
        return None
    from simulation_runtime.mujoco_vla_backend import provenance

    measurement = row.get("measurement")
    if not isinstance(measurement, Mapping):
        return None
    steps, timestep = measurement.get("steps"), measurement.get("timestep_seconds")
    if isinstance(steps, int) and isinstance(timestep, (int, float)):
        simulation_time = {"source": "mujoco_steps_times_timestep", "seconds": steps * timestep}
    elif measurement.get("physics_started") is False:
        simulation_time = {
            "source": "mujoco_no_physics_start",
            "execution_state": {"simulator_started": False, "physics_started": False},
        }
    else:
        return None
    assets = {item.get("path"): item.get("sha256") for item in provenance().get("assets", []) if isinstance(item, Mapping)}
    config = assets.get("configs/simulation/sim005_mujoco_manipulation.yaml")
    model = assets.get("data/simulation/sim005_mujoco_manipulation.xml")
    if not isinstance(config, str) or not isinstance(model, str):
        return None
    return {
        "simulation_time": simulation_time,
        "configuration_sha256": config,
        "world_model_sha256": model,
        "source_paths": {
            "configuration": "configs/simulation/sim005_mujoco_manipulation.yaml",
            "world_model": "data/simulation/sim005_mujoco_manipulation.xml",
        },
    }
