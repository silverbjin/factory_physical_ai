"""Q01 wrappers around accepted simulation execution paths; never write predecessor Evidence."""
from __future__ import annotations

import hashlib
import json
import subprocess
import uuid
from pathlib import Path
from typing import Any

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
        "correlation_identity": correlation,
        "measurement": measurement,
        "provenance": provenance(),
        "semantic_outcome": {"result": result["result"], "status": result["status"], "error": result.get("error")},
    }
