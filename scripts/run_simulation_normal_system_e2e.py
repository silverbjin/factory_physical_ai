#!/usr/bin/env python3
"""Run the bounded TASK-SIM-008 canonical Gazebo system mission."""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))
from simulation_runtime.normal_system_e2e import NormalSystemE2E, GazeboWorldPort, load_scenario, scenario_identity  # noqa: E402
from simulation_runtime.navigation_backend import RuntimeObservation  # noqa: E402


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


class GazeboSystemWorld:
    """Private port coupling the accepted SIM-004 process lifecycle to SIM-008 state."""
    def __init__(self, initial: Mapping[str, str]) -> None:
        from scripts import run_simulation_navigation as navigation_runner
        # SIM-008 owns a tighter end-to-end window than the component runner.
        navigation_runner.STARTUP_SECONDS = 20
        navigation_runner.EXECUTION_SECONDS = 20
        navigation_runner.CLEANUP_SECONDS = 5
        from scripts.run_simulation_navigation import BoundedGazeboNav2Runtime
        self.runtime = BoundedGazeboNav2Runtime()
        self.state = dict(initial)
    @property
    def ready(self) -> bool: return self.runtime.ready
    def start(self) -> None: self.runtime.start()
    def bootstrap_localization(self) -> bool: return self.runtime.bootstrap_localization()
    def navigate(self, request: dict[str, Any]) -> RuntimeObservation: return self.runtime.navigate(request)
    def reconcile(self, action_id: str) -> RuntimeObservation: return self.runtime.reconcile(action_id)
    def observe(self) -> Mapping[str, str]: return dict(self.state)
    def apply_vla_surrogate(self, *, task_id: str, expected_from: Mapping[str, str], expected_to: Mapping[str, str]) -> bool:
        if task_id != "place-brake-ecu" or self.state != dict(expected_from): return False
        self.state = dict(expected_to)
        return True
    def close(self) -> bool: return self.runtime.close()


def _binding(task: str) -> dict[str, Any]:
    path = ROOT / f"results/reviews/{task}_acceptance.json"
    return {"acceptance": json.loads(path.read_text()), "acceptance_sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def main() -> int:
    scenario = load_scenario(); world: GazeboWorldPort = GazeboSystemWorld(scenario["initial_state"])
    outcome = NormalSystemE2E(world, scenario).execute()
    ready = (outcome["mission"]["result"] == "success" and outcome["lifecycle"]["cleanup_complete"] is True and outcome["steps"][-1]["name"] == "final_verification" and outcome["steps"][-1]["result"].get("verdict") == "pass")
    payload = {
        "schema_version": "1.0", "task_id": "TASK-SIM-008", "generated_at": now(),
        "task_specific_result": "SIM_NORMAL_E2E_READY" if ready else "SIM_NORMAL_E2E_BLOCKED",
        "accepted_bindings": {"SIM-007": _binding("SIM-007"), "SIM-005": _binding("SIM-005")},
        "scenario": scenario | scenario_identity(scenario), "system_profile": {"name": "system", "integrated_world": "gazebo_harmonic", "mujoco_live_world": False, "dual_world": False},
        "mujoco_component_evidence": {"live_coupled": False, "purpose": "accepted supporting component proof only", "acceptance": _binding("SIM-005")},
        "execution": outcome, "source_git_sha": subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, capture_output=True, check=False).stdout.strip(),
    }
    path = ROOT / "results/simulation/SIM-008_normal_system_e2e.json"
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(json.dumps(payload, sort_keys=True))
    return 0 if ready else 1


if __name__ == "__main__": raise SystemExit(main())
