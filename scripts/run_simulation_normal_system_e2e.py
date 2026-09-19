#!/usr/bin/env python3
"""Run the bounded TASK-SIM-008 canonical Gazebo system mission."""
from __future__ import annotations

import ast
import hashlib
import json
import subprocess
import sys
import xml.etree.ElementTree as ET
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
    def __init__(self, scenario: Mapping[str, Any]) -> None:
        from scripts import run_simulation_navigation as navigation_runner
        # SIM-008 owns a tighter end-to-end window than the component runner.
        navigation_runner.STARTUP_SECONDS = 20
        navigation_runner.EXECUTION_SECONDS = 20
        navigation_runner.CLEANUP_SECONDS = 5
        from scripts.run_simulation_navigation import BoundedGazeboNav2Runtime
        self.scenario = dict(scenario)
        self.world_name = Path(str(scenario["world"])).stem
        self.entity_name = str(scenario["object"]["gazebo_entity_name"])
        self.runtime = BoundedGazeboNav2Runtime(ROOT / str(scenario["world"]))
    @property
    def ready(self) -> bool: return self.runtime.ready
    def start(self) -> None: self.runtime.start()
    def bootstrap_localization(self) -> bool: return self.runtime.bootstrap_localization()
    def navigate(self, request: dict[str, Any]) -> RuntimeObservation: return self.runtime.navigate(request)
    def reconcile(self, action_id: str) -> RuntimeObservation: return self.runtime.reconcile(action_id)
    def _run_gz(self, command: list[str], *, timeout: float = 5) -> subprocess.CompletedProcess[str]:
        completed = subprocess.run(command, text=True, capture_output=True, timeout=timeout, check=False, env=self.runtime.environment)
        self.runtime.measurements.setdefault("world_state", []).append({"command": command, "returncode": completed.returncode, "stdout_tail": completed.stdout[-1000:], "stderr_tail": completed.stderr[-1000:]})
        if completed.returncode != 0:
            raise RuntimeError(f"Gazebo world command failed: {completed.stderr.strip() or completed.stdout.strip()}")
        return completed
    def observe(self) -> Mapping[str, Any]:
        service = f"/world/{self.world_name}/generate_world_sdf"
        snapshot_result = self._run_gz(["gz", "service", "-s", service, "--reqtype", "gz.msgs.SdfGeneratorConfig", "--reptype", "gz.msgs.StringMsg", "--timeout", "5000", "--req", ""])
        try:
            snapshot = ast.literal_eval(snapshot_result.stdout.split("data:", 1)[1].strip())
        except (IndexError, SyntaxError, ValueError) as exc:
            raise RuntimeError("Gazebo world snapshot response is malformed") from exc
        stats_topic = f"/world/{self.world_name}/stats"
        stats_result = self._run_gz(["gz", "topic", "-e", "-n", "1", "--json-output", "-t", stats_topic])
        try:
            stats = json.loads(stats_result.stdout)
            sim_time = {"sec": int(stats["simTime"]["sec"]), "nsec": int(stats["simTime"].get("nsec", 0))}
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise RuntimeError("Gazebo simulation time observation is malformed") from exc
        return parse_authoritative_world_snapshot(snapshot, self.scenario, observed_at=now(), simulation_time=sim_time)
    def apply_vla_surrogate(self, *, task_id: str, expected_from: Mapping[str, str], expected_to: Mapping[str, str]) -> bool:
        if task_id != "place-brake-ecu" or self.observe()["semantic_state"] != dict(expected_from): return False
        destination = next((region for region in self.scenario["regions"].values() if region["id"] == expected_to["location_id"]), None)
        if destination is None or expected_to.get("part_id") != self.scenario["object"]["part_id"]: return False
        request = f'name: "{self.entity_name}", position: {{x: {destination["x"]}, y: {destination["y"]}, z: {destination["z"]}}}, orientation: {{w: 1.0}}'
        result = self._run_gz(["gz", "service", "-s", f"/world/{self.world_name}/set_pose", "--reqtype", "gz.msgs.Pose", "--reptype", "gz.msgs.Boolean", "--timeout", "5000", "--req", request])
        return "data: true" in result.stdout.lower()
    def close(self) -> bool: return self.runtime.close()


def _binding(task: str) -> dict[str, Any]:
    path = ROOT / f"results/reviews/{task}_acceptance.json"
    return {"acceptance": json.loads(path.read_text()), "acceptance_sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def parse_authoritative_world_snapshot(snapshot: str, scenario: Mapping[str, Any], *, observed_at: str, simulation_time: Mapping[str, int]) -> dict[str, Any]:
    """Derive semantic state from one live Gazebo-generated world snapshot."""
    parseable_snapshot = snapshot
    if "xacro:" in parseable_snapshot and "xmlns:xacro" not in parseable_snapshot:
        parseable_snapshot = parseable_snapshot.replace("<sdf ", '<sdf xmlns:xacro="http://www.ros.org/wiki/xacro" ', 1)
    # Gazebo serializes the dynamically spawned TB4's synthetic URI without
    # XML escaping. Escape only that known transport placeholder before parsing.
    parseable_snapshot = parseable_snapshot.replace("file://<urdf-string>", "file://&lt;urdf-string&gt;")
    try:
        root = ET.fromstring(parseable_snapshot)
    except ET.ParseError as exc:
        raise RuntimeError("Gazebo world snapshot XML is malformed") from exc
    expected_world = Path(str(scenario["world"])).stem
    world = root.find(f"./world[@name='{expected_world}']")
    entity_name = str(scenario["object"]["gazebo_entity_name"])
    model = None if world is None else world.find(f"./model[@name='{entity_name}']")
    pose_element = None if model is None else model.find("pose")
    if pose_element is None or not pose_element.text:
        raise RuntimeError("authoritative Gazebo entity pose is unavailable")
    try:
        values = [float(value) for value in pose_element.text.split()]
    except ValueError as exc:
        raise RuntimeError("authoritative Gazebo entity pose is malformed") from exc
    if len(values) < 3:
        raise RuntimeError("authoritative Gazebo entity pose is malformed")
    pose = {"x": values[0], "y": values[1], "z": values[2]}
    matching = [region for region in scenario["regions"].values() if all(abs(float(region[axis]) - pose[axis]) <= 0.05 for axis in ("x", "y", "z"))]
    if len(matching) != 1:
        raise RuntimeError("authoritative Gazebo entity pose does not resolve to one task region")
    return {
        "runtime_backend": "gz_sim_harmonic",
        "observation_source": f"/world/{expected_world}/generate_world_sdf",
        "world_name": expected_world,
        "entity_id": str(scenario["object"]["id"]),
        "entity_name": entity_name,
        "pose": pose,
        "semantic_state": {"part_id": str(scenario["object"]["part_id"]), "location_id": str(matching[0]["id"])},
        "observed_at": observed_at,
        "simulation_time": {"sec": int(simulation_time["sec"]), "nsec": int(simulation_time["nsec"])},
        "snapshot_sha256": hashlib.sha256(snapshot.encode()).hexdigest(),
    }


def main() -> int:
    scenario = load_scenario(); world: GazeboWorldPort = GazeboSystemWorld(scenario)
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
