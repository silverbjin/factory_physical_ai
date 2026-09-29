from __future__ import annotations

import sys
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Mapping

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from simulation_runtime.normal_system_e2e import InMemoryGazeboWorld, NormalSystemE2E, load_scenario, scenario_identity
from simulation_runtime.navigation_backend import RuntimeObservation
from simulation_runtime.smoke import validate_contract_message
from scripts import run_simulation_normal_system_e2e as system_runner


class AuthoritativeWorldDouble:
    """Test-only double whose observations are independent runtime records."""

    def __init__(self, state: Mapping[str, str], *, observation_available: bool = True,
                 observed_at: str | None = None, observation_clock: Callable[[], datetime] | None = None,
                 on_navigate: Callable[[], None] | None = None,
                 on_vla: Callable[[], None] | None = None) -> None:
        self.observed_state = dict(state)
        self.observation_available = observation_available
        self.observed_at = observed_at
        self.observation_clock = observation_clock
        self.on_navigate = on_navigate
        self.on_vla = on_vla
        self.ready = True
        self.closed = False

    def start(self) -> None: pass
    def bootstrap_localization(self) -> bool: return True
    def navigate(self, request: dict[str, Any]) -> RuntimeObservation:
        if self.on_navigate is not None:
            self.on_navigate()
        return RuntimeObservation("succeeded", arrival_verified=True)
    def reconcile(self, action_id: str) -> RuntimeObservation:
        return RuntimeObservation("succeeded", arrival_verified=True)
    def observe(self) -> Mapping[str, Any]:
        if not self.observation_available:
            raise RuntimeError("authoritative Gazebo observation unavailable")
        x = -6.5 if self.observed_state["location_id"] == "warehouse-a" else -6.0
        return {
            "runtime_backend": "gz_sim_harmonic",
            "observation_source": "/world/sim008_normal_system_world/generate_world_sdf",
            "world_name": "sim008_normal_system_world",
            "entity_id": "brake-ecu-type-b-001",
            "entity_name": "brake_ecu_type_b_001",
            "pose": {"x": x, "y": 0.0, "z": 0.2},
            "semantic_state": dict(self.observed_state),
            "observed_at": self.observed_at or (self.observation_clock or (lambda: datetime.now(timezone.utc)))().isoformat(timespec="milliseconds").replace("+00:00", "Z"),
            "simulation_time": {"sec": 1, "nsec": 0},
            "snapshot_sha256": "a" * 64,
        }
    def apply_vla_surrogate(self, *, task_id: str, expected_from: Mapping[str, str], expected_to: Mapping[str, str]) -> bool:
        if task_id != "place-brake-ecu" or self.observed_state != dict(expected_from):
            return False
        self.observed_state = dict(expected_to)
        if self.on_vla is not None:
            self.on_vla()
        return True

    def close(self) -> bool:
        self.closed = True
        return True


class ManualClock:
    def __init__(self) -> None:
        self.value = datetime(2026, 9, 18, tzinfo=timezone.utc)

    def __call__(self) -> datetime:
        return self.value

    def advance(self, seconds: int) -> None:
        self.value += timedelta(seconds=seconds)


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
    world = AuthoritativeWorldDouble(scenario["initial_state"])
    outcome = NormalSystemE2E(world, scenario).execute()
    assert outcome["mission"]["result"] == "success"
    assert outcome["transitions"][-1] == {"from": "executing", "to": "completed"}
    assert outcome["steps"][-1]["name"] == "final_verification"
    assert outcome["steps"][-1]["result"]["verdict"] == "pass"
    assert [step["name"] for step in outcome["steps"]] == ["source_navigation", "source_verification", "destination_navigation", "vla.execute", "final_verification"]
    assert world.observed_state == {"part_id": "brake-ecu-b", "location_id": "line-b-drop"}
    assert world.closed
    assert outcome["steps"][-1]["observation"]["entity_id"] == "brake-ecu-type-b-001"
    assert outcome["steps"][-1]["expected_state"] == {"part_id": "brake-ecu-b", "location_id": "line-b-drop"}
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
    scenario = load_scenario(); world = AuthoritativeWorldDouble({"part_id": "wrong", "location_id": "warehouse-a"})
    outcome = NormalSystemE2E(world, scenario).execute()
    assert outcome["mission"]["result"] == "failure"
    assert outcome["lifecycle"]["cleanup_complete"] is True


def test_process_local_state_cannot_satisfy_authoritative_acceptance() -> None:
    scenario = load_scenario()
    process_local_world = InMemoryGazeboWorld(dict(scenario["initial_state"]))
    outcome = NormalSystemE2E(process_local_world, scenario).execute()
    assert outcome["mission"]["result"] == "failure"
    assert "authoritative" in outcome["mission"]["error"]["message"].lower()


def test_unavailable_authoritative_observation_fails_closed() -> None:
    scenario = load_scenario()
    world = AuthoritativeWorldDouble(scenario["initial_state"], observation_available=False)
    outcome = NormalSystemE2E(world, scenario).execute()
    assert outcome["mission"]["result"] == "failure"
    assert outcome["lifecycle"]["cleanup_complete"] is True


def test_stale_authoritative_observation_fails_closed() -> None:
    scenario = load_scenario()
    stale = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat().replace("+00:00", "Z")
    outcome = NormalSystemE2E(AuthoritativeWorldDouble(scenario["initial_state"], observed_at=stale), scenario).execute()
    assert outcome["mission"]["result"] == "failure"
    assert "stale" in outcome["mission"]["error"]["message"].lower()


def test_mission_succeeds_when_completed_inside_deadline() -> None:
    scenario = load_scenario()
    clock = ManualClock()
    world = AuthoritativeWorldDouble(scenario["initial_state"], observation_clock=clock)
    outcome = NormalSystemE2E(world, scenario, clock=clock).execute()
    assert outcome["mission"]["result"] == "success"


def test_expiry_before_final_success_fails_closed() -> None:
    scenario = load_scenario()
    clock = ManualClock()
    world = AuthoritativeWorldDouble(
        scenario["initial_state"], observation_clock=clock,
        on_vla=lambda: clock.advance(31),
    )
    outcome = NormalSystemE2E(world, scenario, clock=clock).execute()
    assert outcome["mission"]["result"] == "failure"
    assert outcome["mission"]["error"]["code"] == "MISSION_DEADLINE_EXCEEDED"
    assert outcome["lifecycle"]["cleanup_complete"] is True


def test_expiry_during_intermediate_action_fails_closed() -> None:
    scenario = load_scenario()
    clock = ManualClock()
    world = AuthoritativeWorldDouble(
        scenario["initial_state"], observation_clock=clock,
        on_navigate=lambda: clock.advance(31),
    )
    outcome = NormalSystemE2E(world, scenario, clock=clock).execute()
    assert outcome["mission"]["result"] == "failure"
    assert outcome["mission"]["error"]["code"] == "MISSION_DEADLINE_EXCEEDED"
    assert outcome["lifecycle"]["cleanup_complete"] is True


def test_generated_world_snapshot_is_independently_mapped_to_semantic_state() -> None:
    parser = getattr(system_runner, "parse_authoritative_world_snapshot", None)
    assert parser is not None, "authoritative Gazebo snapshot parser is required"
    scenario = load_scenario()
    snapshot = """<sdf version='1.10'><world name='sim008_normal_system_world'>
      <xacro:unless value='true'><plugin name='scene'/></xacro:unless>
      <model name='brake_ecu_type_b_001'><pose>-6 0 0.2 0 0 0</pose></model>
      <include><uri>file://<urdf-string></uri><name>turtlebot4</name></include>
    </world></sdf>"""
    record = parser(
        snapshot,
        scenario,
        observed_at="2026-09-18T02:00:00.000Z",
        simulation_time={"sec": 42, "nsec": 7},
    )
    assert record["semantic_state"] == {"part_id": "brake-ecu-b", "location_id": "line-b-drop"}
    assert record["pose"] == {"x": -6.0, "y": 0.0, "z": 0.2}
    assert record["snapshot_sha256"] != "a" * 64
