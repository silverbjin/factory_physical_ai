from __future__ import annotations

import sys
import uuid
from dataclasses import FrozenInstanceError
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import yaml
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from simulation_runtime.navigation_backend import (  # noqa: E402
    NavigationBackend, RuntimeObservation, provenance,
)
from simulation_runtime.smoke import validate_contract_message  # noqa: E402
from scripts import run_simulation_navigation as navigation_runner  # noqa: E402
from scripts.run_simulation_navigation import BoundedGazeboNav2Runtime, CANONICAL_START, initial_pose_message, lifecycle_is_active, terminal_action_status, transform_observed  # noqa: E402

NavigationRuntimeBounds = getattr(navigation_runner, "NavigationRuntimeBounds", None)
NavigationReadinessResult = getattr(navigation_runner, "NavigationReadinessResult", None)


def request(destination: str = "line-b-drop") -> dict[str, object]:
    now = datetime.now(timezone.utc)
    return {"operation": "navigation.execute", "message_type": "request", "schema_version": "1.0", "mission_id": str(uuid.uuid4()), "request_id": str(uuid.uuid4()), "trace_id": str(uuid.uuid4()), "idempotency_key": "test-navigation", "action_id": str(uuid.uuid4()), "timestamp": now.isoformat().replace("+00:00", "Z"), "deadline_at": (now + timedelta(seconds=1)).isoformat().replace("+00:00", "Z"), "timeout_ms": 1000, "component_version": "test", "attempt": 1, "retry_budget_remaining": 1, "robot_id": "simulation-proxy-mobile-base", "destination_id": destination, "speed_profile_id": "sim-safe-v1"}


def status_request(execute: dict[str, object]) -> dict[str, object]:
    return {key: execute[key] for key in ("schema_version", "mission_id", "trace_id", "timestamp", "deadline_at", "timeout_ms", "component_version", "action_id")} | {"operation": "action_status.get", "message_type": "request", "request_id": str(uuid.uuid4())}


class RecordedRuntime:
    """Test double for the private Nav2-facing runtime boundary."""

    ready = True

    def __init__(self, observation: RuntimeObservation, reconciled: RuntimeObservation | None = None) -> None:
        self.observation = observation
        self.reconciled = reconciled or observation

    def navigate(self, request: dict[str, object]) -> RuntimeObservation:
        return self.observation

    def reconcile(self, action_id: str) -> RuntimeObservation:
        return self.reconciled


def test_success_is_contract_valid_and_arrives_at_requested_destination() -> None:
    req = request(); result = NavigationBackend(RecordedRuntime(RuntimeObservation("succeeded", arrival_verified=True))).execute(req)
    validate_contract_message(result)
    assert result["result"] == "success" and result["arrival"]["destination_id"] == req["destination_id"]


def test_invalid_unavailable_and_blocked_fail_closed() -> None:
    assert NavigationBackend().execute(request("not-allowlisted"))["result"] == "failure"
    assert NavigationBackend().execute(request())["error"]["category"] == "RESOURCE_UNAVAILABLE"
    failed = NavigationBackend(RecordedRuntime(RuntimeObservation("failed"))).execute(request("blocked-bay"))
    assert failed["status"] == "failed"


def test_timeout_stays_unknown_until_authoritative_status_lookup() -> None:
    backend = NavigationBackend(RecordedRuntime(
        RuntimeObservation("unknown", error_code="NAVIGATION_TIMEOUT", error_message="bounded timeout", error_category="DEPENDENCY_TIMEOUT", retryable=True),
        RuntimeObservation("succeeded", arrival_verified=True),
    ))
    req = request(); timeout = backend.execute(req)
    lookup = backend.action_status_get(status_request(req))
    validate_contract_message(timeout); validate_contract_message(lookup)
    assert timeout["result"] == "pending" and timeout["status"] == "unknown"
    assert timeout["action_id"] == lookup["action_id"] == req["action_id"]
    assert lookup["observed_status"] == "succeeded"


def test_provenance_is_hashed_and_explicitly_nonphysical() -> None:
    info = provenance()
    assert info["baseline_id"] == "SIM_BASELINE_V1" and info["physical_target"] is False
    assert len(info["assets"]) == 4 and all(len(item["sha256"]) == 64 for item in info["assets"])


def test_lifecycle_readiness_requires_the_canonical_active_state() -> None:
    assert lifecycle_is_active("active [3]\n")
    assert not lifecycle_is_active("inactive [2]\n")
    assert not lifecycle_is_active("node is active but state is unknown")


def test_tf_output_requires_an_observed_transform_not_process_completion() -> None:
    assert transform_observed("At time 12.0\n- Translation: [1, 2, 3]\n- Rotation: [0, 0, 0, 1]\n")
    assert not transform_observed("Waiting for transform odom -> base_link\n")
    assert not transform_observed('Invalid frame ID "odom"\n')


def test_canonical_start_is_shared_and_action_terminal_status_fails_closed() -> None:
    assert CANONICAL_START["x"] == -6.5 and CANONICAL_START["frame_id"] == "map"
    assert terminal_action_status("Goal finished with status: SUCCEEDED") == "SUCCEEDED"
    assert terminal_action_status("Goal finished with status: ABORTED") == "ABORTED"
    assert terminal_action_status("goal accepted") is None


def test_initial_pose_message_is_a_ros_yaml_pose_with_covariance() -> None:
    message = initial_pose_message(CANONICAL_START)
    parsed = yaml.safe_load(message)
    assert parsed["header"]["frame_id"] == "map"
    assert parsed["pose"]["pose"]["position"] == {"x": -6.5, "y": 0.0, "z": 0.0}
    assert len(parsed["pose"]["covariance"]) == 36


def test_localization_waits_for_clock_initial_pose_and_delayed_map_to_odom() -> None:
    runtime = object.__new__(BoundedGazeboNav2Runtime)
    runtime.measurements = {"readiness": []}
    runtime.initial_pose = {"frame_id": "map", "x": -1.25, "y": 2.5, "yaw": 0.0, "source": "scenario"}
    runtime.bounds = NavigationRuntimeBounds()
    runtime._ready = False
    probes: list[str] = []
    transforms = {"odom_to_base": [True], "map_to_odom": [False, True]}
    clocks = ["", "clock:\n  sec: 1\n  nanosec: 0\n"]

    def probe(label: str, _command: list[str], _timeout: float = 10):
        probes.append(label)
        if label == "localization_topics":
            return SimpleNamespace(returncode=0, stdout="/map\n/scan\n/odom\n")
        if label == "simulation_clock":
            return SimpleNamespace(returncode=0, stdout=clocks.pop(0) if len(clocks) > 1 else clocks[0])
        if label in {"map_server_lifecycle", "amcl_lifecycle", "bt_navigator_lifecycle"}:
            return SimpleNamespace(returncode=0, stdout="active [3]\n")
        if label == "navigate_to_pose_action":
            return SimpleNamespace(returncode=0, stdout="/navigate_to_pose [nav2_msgs/action/NavigateToPose]\n")
        return SimpleNamespace(returncode=0, stdout="")

    def probe_tf(label: str, *_args, **_kwargs) -> bool:
        return transforms[label].pop(0)

    runtime._probe = probe
    runtime._probe_tf = probe_tf
    with patch("scripts.run_simulation_navigation.time.sleep"):
        assert runtime.bootstrap_localization() is True

    assert probes.index("simulation_clock") < probes.index("localization_topics")
    assert probes.index("initial_pose_publish") < probes.index("navigation_lifecycle_start")
    assert runtime._ready is True


def test_localization_fails_closed_when_map_to_odom_never_arrives() -> None:
    runtime = object.__new__(BoundedGazeboNav2Runtime)
    runtime.measurements = {"readiness": []}
    runtime.initial_pose = dict(CANONICAL_START)
    runtime.bounds = NavigationRuntimeBounds(localization_seconds=0)
    runtime._ready = False

    def probe(label: str, _command: list[str], _timeout: float = 10):
        if label == "localization_topics":
            return SimpleNamespace(returncode=0, stdout="/map\n/scan\n/odom\n")
        if label == "simulation_clock":
            return SimpleNamespace(returncode=0, stdout="clock:\n  sec: 1\n  nanosec: 0\n")
        if label in {"map_server_lifecycle", "amcl_lifecycle", "bt_navigator_lifecycle"}:
            return SimpleNamespace(returncode=0, stdout="active [3]\n")
        return SimpleNamespace(returncode=0, stdout="")

    runtime._probe = probe
    runtime._probe_tf = lambda label, *_args, **_kwargs: label == "odom_to_base"
    assert runtime.bootstrap_localization() is False
    assert runtime.ready is False


def test_cleanup_terminates_launch_owned_child_process_groups() -> None:
    """A ros2 launch child group must not outlive its bounded runtime owner."""
    runtime = object.__new__(BoundedGazeboNav2Runtime)
    runtime.measurements = {"processes": [{}]}
    runtime.log_files = []
    runtime.bounds = NavigationRuntimeBounds(cleanup_seconds=0)

    class Process:
        pid = 100
        returncode = None

        def poll(self):
            return self.returncode

        def wait(self, timeout):
            return self.returncode

    process = Process()
    runtime.processes = [process]
    terminated_groups: list[int] = []

    def killpg(pgid: int, _signal: int) -> None:
        terminated_groups.append(pgid)
        process.returncode = -15

    process_table = "100 1 100\n101 100 101\n102 101 101\n900 1 900\n"
    with patch("scripts.run_simulation_navigation.subprocess.run") as run, \
         patch("scripts.run_simulation_navigation.os.getpgid", return_value=100), \
         patch("scripts.run_simulation_navigation.os.killpg", side_effect=killpg):
        run.return_value = SimpleNamespace(returncode=0, stdout=process_table)
        assert runtime.close() is True

    assert 100 in terminated_groups
    assert 101 in terminated_groups
    assert 900 not in terminated_groups


def test_runtime_uses_a_fresh_dds_domain_without_ros_cli_daemon_cache() -> None:
    """Independent bounded launches cannot discover a previous run's graph."""
    first = BoundedGazeboNav2Runtime()
    second = BoundedGazeboNav2Runtime()

    assert first.environment["ROS_DOMAIN_ID"] != second.environment["ROS_DOMAIN_ID"]
    assert first.environment["ROS_DOMAIN_ID"] != "44"
    assert first.environment["ROS2CLI_USE_DAEMON"] == "0"
    assert second.environment["ROS2CLI_USE_DAEMON"] == "0"


def test_runtime_materializes_the_ros_jazzy_launch_environment() -> None:
    """The live runtime must not depend on an implicitly sourced parent shell."""
    runtime = BoundedGazeboNav2Runtime()

    assert runtime.environment["ROS_DISTRO"] == "jazzy"
    assert "/opt/ros/jazzy" in runtime.environment["AMENT_PREFIX_PATH"].split(":")
    assert "/opt/ros/jazzy/lib/python3.12/site-packages" in runtime.environment["PYTHONPATH"].split(":")
    assert "/opt/ros/jazzy/lib" in runtime.environment["LD_LIBRARY_PATH"].split(":")
    assert "/opt/ros/jazzy/lib" in runtime.environment["GZ_SIM_SYSTEM_PLUGIN_PATH"].split(":")


def test_runtime_bounds_are_immutable_and_instance_local() -> None:
    assert NavigationRuntimeBounds is not None, "immutable per-run bounds are required"
    first_bounds = NavigationRuntimeBounds(
        startup_seconds=2, localization_seconds=3,
        execution_seconds=4, cleanup_seconds=5,
    )
    first = BoundedGazeboNav2Runtime(bounds=first_bounds)
    second = BoundedGazeboNav2Runtime()

    assert first.bounds == first_bounds
    assert second.bounds == NavigationRuntimeBounds()
    assert first.bounds is not second.bounds
    with pytest.raises(FrozenInstanceError):
        first.bounds.startup_seconds = 99  # type: ignore[misc]


def test_launch_and_localization_use_the_same_authoritative_pose() -> None:
    assert NavigationRuntimeBounds is not None, "immutable per-run bounds are required"
    pose = {"frame_id": "map", "x": -1.25, "y": 2.5, "yaw": 0.75, "source": "test scenario"}
    runtime = BoundedGazeboNav2Runtime(
        initial_pose=pose,
        bounds=NavigationRuntimeBounds(startup_seconds=0),
    )
    commands: list[list[str]] = []
    runtime._start = lambda _name, command: commands.append(command)

    runtime.start()

    command = commands[0]
    assert "x_pose:=-1.25" in command
    assert "y_pose:=2.5" in command
    assert "yaw:=0.75" in command
    assert runtime.initial_pose == pose


def test_shared_session_preserves_the_first_failed_readiness_stage() -> None:
    assert NavigationReadinessResult is not None, "structured session readiness is required"
    runtime = object.__new__(BoundedGazeboNav2Runtime)
    runtime.measurements = {"readiness": []}
    runtime._ready = False
    runtime.bootstrap_error = None
    runtime.start = lambda: (_ for _ in ()).throw(RuntimeError("launch exploded"))

    result = runtime.establish_readiness()

    assert result.ready is False
    assert result.stage == "LAUNCH"
    assert result.error == "RuntimeError: launch exploded"
    assert runtime.measurements["session_readiness"] == result.as_dict()


def test_shared_session_classifies_clock_failure_without_erasing_reason() -> None:
    assert NavigationReadinessResult is not None, "structured session readiness is required"
    runtime = object.__new__(BoundedGazeboNav2Runtime)
    runtime.measurements = {"readiness": []}
    runtime._ready = False
    runtime.bootstrap_error = "SIMULATION_CLOCK_UNAVAILABLE"
    runtime.start = lambda: None
    runtime.bootstrap_localization = lambda: False

    result = runtime.establish_readiness()

    assert result.ready is False
    assert result.stage == "CLOCK"
    assert result.error == "SIMULATION_CLOCK_UNAVAILABLE"
