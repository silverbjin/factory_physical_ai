"""Q01 wrappers around accepted simulation execution paths; never write predecessor Evidence."""
from __future__ import annotations

import hashlib
import json
import subprocess
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
