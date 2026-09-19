from __future__ import annotations

import sys
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from simulation_runtime.normal_system_e2e import InMemoryGazeboWorld, NormalSystemE2E, load_scenario, scenario_identity
from simulation_runtime.smoke import validate_contract_message


def test_system_e2e_import_does_not_require_mujoco_component_backend() -> None:
    """The Gazebo-only E2E entry point must not load the separate MuJoCo backend."""
    completed = subprocess.run(
        [sys.executable, "-c", "import sys; sys.path.insert(0, 'src'); import simulation_runtime.normal_system_e2e"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr


def test_canonical_system_mission_is_gazebo_only_and_verifies_before_completion() -> None:
    scenario = load_scenario()
    world = InMemoryGazeboWorld(dict(scenario["initial_state"]))
    outcome = NormalSystemE2E(world, scenario).execute()
    assert outcome["mission"]["result"] == "success"
    assert outcome["transitions"][-1] == {"from": "executing", "to": "completed"}
    assert outcome["steps"][-1]["name"] == "final_verification"
    assert outcome["steps"][-1]["result"]["verdict"] == "pass"
    assert [step["name"] for step in outcome["steps"]] == ["source_navigation", "source_verification", "vla.execute", "destination_navigation", "final_verification"]
    assert world.state == {"part_id": "brake-ecu-b", "location_id": "line-b-drop"}
    assert world.closed and "vla.execute" in world.calls
    validate_contract_message(outcome["mission"])
    for step in outcome["steps"]:
        if "request" in step: validate_contract_message(step["request"])
        validate_contract_message(step["result"])


def test_scenario_identity_binds_task_owned_world_and_configuration() -> None:
    scenario = load_scenario(); identity = scenario_identity(scenario)
    assert scenario["scenario_id"] == "SIM_NORMAL_BRAKE_ECU_LINE_B"
    assert scenario["regions"]["source"]["id"] == "warehouse-a"
    assert scenario["regions"]["destination"]["id"] == "line-b-drop"
    assert all(len(identity[key]) == 64 for key in ("scenario_sha256", "world_sha256", "config_sha256"))


def test_surrogate_failure_cannot_complete_mission() -> None:
    scenario = load_scenario(); world = InMemoryGazeboWorld({"part_id": "wrong", "location_id": "warehouse-a"})
    outcome = NormalSystemE2E(world, scenario).execute()
    assert outcome["mission"]["result"] == "failure"
    assert outcome["lifecycle"]["cleanup_complete"] is True
