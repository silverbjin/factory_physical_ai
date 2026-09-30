#!/usr/bin/env python3
"""Run SIM-004 against a bounded Gazebo Harmonic + ROS 2 + Nav2 process set.

The runner is intentionally fail-closed: it writes BLOCKED evidence whenever a
real process cannot become ready, a scenario cannot be observed, or cleanup is
not verified.  It never substitutes an in-memory success for a runtime result.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import selectors
import signal
import subprocess
import sys
import tempfile
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from simulation_runtime.navigation_backend import (  # noqa: E402
    NavigationBackend, RuntimeObservation, provenance,
)

ROS2 = "/opt/ros/jazzy/bin/ros2"
ROS_SETUP = Path("/opt/ros/jazzy/setup.bash")
STARTUP_SECONDS = 45
EXECUTION_SECONDS = 30
CLEANUP_SECONDS = 5
LOCALIZATION_SECONDS = 30
# depot.yaml's cell at (-6.5, 0.0) is free (254); it is inside the published
# map and connected to the unchanged line-b-drop goal at (-6.0, 0.0).
CANONICAL_START = {"frame_id": "map", "x": -6.5, "y": 0.0, "yaw": 0.0,
                   "source": "depot.yaml free cell at (-6.5, 0.0), verified against map origin/resolution"}
GOALS = {
    "warehouse-a": "{pose: {header: {frame_id: map}, pose: {position: {x: -6.5, y: 0.0, z: 0.0}, orientation: {w: 1.0}}}}",
    "line-b-drop": "{pose: {header: {frame_id: map}, pose: {position: {x: -6.0, y: 0.0, z: 0.0}, orientation: {w: 1.0}}}}",
    "blocked-bay": "{pose: {header: {frame_id: map}, pose: {position: {x: 100.0, y: 100.0, z: 0.0}, orientation: {w: 1.0}}}}",
}


@dataclass(frozen=True, slots=True)
class NavigationRuntimeBounds:
    """Immutable bounds owned by one navigation runtime instance."""

    startup_seconds: float = STARTUP_SECONDS
    localization_seconds: float = LOCALIZATION_SECONDS
    execution_seconds: float = EXECUTION_SECONDS
    cleanup_seconds: float = CLEANUP_SECONDS


@dataclass(frozen=True, slots=True)
class NavigationRuntimeContext:
    """One run's immutable launch, localization, and isolation authority."""

    world_path: Path
    initial_pose: Mapping[str, object]
    bounds: NavigationRuntimeBounds
    environment: Mapping[str, str]
    ros_domain_id: str
    gazebo_partition: str
    ros_log_dir: str

    @classmethod
    def create(
        cls,
        *,
        world_path: Path,
        initial_pose: Mapping[str, object],
        bounds: NavigationRuntimeBounds,
        base_environment: Mapping[str, str],
    ) -> "NavigationRuntimeContext":
        environment = ros_runtime_environment(base_environment)
        log_dir = tempfile.mkdtemp(prefix="sim004-ros-", dir="/tmp")
        run_token = uuid.uuid4().hex
        ros_domain_id = str(1 + (int(run_token[:8], 16) % 232))
        gazebo_partition = f"sim004-{run_token[:12]}"
        environment.update({
            "ROS_LOG_DIR": log_dir,
            "ROS_DOMAIN_ID": ros_domain_id,
            "ROS2CLI_USE_DAEMON": "0",
            "GZ_PARTITION": gazebo_partition,
        })
        return cls(
            world_path=world_path,
            initial_pose=MappingProxyType(dict(initial_pose)),
            bounds=bounds,
            environment=MappingProxyType(environment),
            ros_domain_id=ros_domain_id,
            gazebo_partition=gazebo_partition,
            ros_log_dir=log_dir,
        )


@dataclass(frozen=True, slots=True)
class NavigationReadinessResult:
    """Structured result for the shared Gazebo/Nav2 readiness lifecycle."""

    ready: bool
    stage: str
    error: str | None = None

    def as_dict(self) -> dict[str, object]:
        return {"ready": self.ready, "stage": self.stage, "error": self.error}


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def lifecycle_is_active(output: str) -> bool:
    """Only Nav2's canonical active lifecycle state is readiness proof."""
    return "active [3]" in output.lower()


def transform_observed(output: str) -> bool:
    """Recognize tf2_echo's emitted transform, not its intentionally open lifetime."""
    normalized = output.lower()
    return "at time" in normalized and "translation:" in normalized and "rotation:" in normalized


def clock_observed(output: str) -> bool:
    """Require a structured ROS clock message, not process liveness."""
    normalized = output.lower()
    return "sec:" in normalized and ("nanosec:" in normalized or "nsec:" in normalized)


def initial_pose_message(pose: Mapping[str, object]) -> str:
    """Render the task-authoritative AMCL pose as a ROS 2 CLI message."""
    try:
        frame_id = str(pose["frame_id"])
        x, y, yaw = (float(pose[name]) for name in ("x", "y", "yaw"))
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("INVALID_LOCALIZATION_INITIAL_POSE") from exc
    half_yaw = yaw / 2.0
    return (
        f"{{header: {{frame_id: {frame_id}}}, pose: {{pose: {{position: {{x: {x}, y: {y}, z: 0.0}}, "
        f"orientation: {{z: {math.sin(half_yaw)}, w: {math.cos(half_yaw)}}}}}, covariance: "
        "[0.25, 0, 0, 0, 0, 0, 0, 0.25, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]}}"
    )


def terminal_action_status(output: str) -> str | None:
    for status in ("SUCCEEDED", "ABORTED", "CANCELED"):
        if f"Goal finished with status: {status}" in output:
            return status
    return None


def ros_runtime_environment(base_environment: Mapping[str, str]) -> dict[str, str]:
    """Materialize the authoritative ROS installation environment.

    The runtime is invoked by non-interactive workers whose parent shell is
    not guaranteed to have sourced ROS.  Capturing ``setup.bash`` once gives
    the launch process and every probe the same explicit ROS/Gazebo paths.
    """
    completed = subprocess.run(
        [
            "/bin/bash", "--noprofile", "--norc", "-c",
            'source "$1" && env -0', "q01-ros-runtime", str(ROS_SETUP),
        ],
        env=dict(base_environment), capture_output=True, check=False,
    )
    if completed.returncode != 0:
        error = completed.stderr.decode(errors="replace").strip()
        raise RuntimeError(f"ROS_RUNTIME_ENVIRONMENT_UNAVAILABLE: {error or completed.returncode}")
    environment: dict[str, str] = {}
    for item in completed.stdout.split(b"\0"):
        if b"=" not in item:
            continue
        key, value = item.split(b"=", 1)
        environment[key.decode(errors="surrogateescape")] = value.decode(errors="surrogateescape")
    return environment


def request(destination: str = "line-b-drop", timeout_ms: int = 30000) -> dict[str, object]:
    stamp = datetime.now(timezone.utc)
    return {"operation": "navigation.execute", "message_type": "request", "schema_version": "1.0", "mission_id": str(uuid.uuid4()), "request_id": str(uuid.uuid4()), "trace_id": str(uuid.uuid4()), "idempotency_key": "sim004-navigation", "action_id": str(uuid.uuid4()), "timestamp": stamp.isoformat().replace("+00:00", "Z"), "deadline_at": (stamp + timedelta(milliseconds=timeout_ms)).isoformat().replace("+00:00", "Z"), "timeout_ms": timeout_ms, "component_version": "sim004-runner-v2", "attempt": 1, "retry_budget_remaining": 1, "robot_id": "simulation-proxy-mobile-base", "destination_id": destination, "speed_profile_id": "sim-safe-v1"}


class BoundedGazeboNav2Runtime:
    """Private ROS action implementation with process-group lifecycle control."""

    def __init__(
        self,
        world_path: Path | None = None,
        *,
        initial_pose: Mapping[str, object] | None = None,
        bounds: NavigationRuntimeBounds | None = None,
        context: NavigationRuntimeContext | None = None,
    ) -> None:
        if context is not None and any(value is not None for value in (world_path, initial_pose, bounds)):
            raise ValueError("RUNTIME_CONTEXT_CONFLICT")
        if context is None:
            context = NavigationRuntimeContext.create(
                world_path=world_path or ROOT / "data/simulation/sim004_navigation_proxy_world.sdf",
                initial_pose=CANONICAL_START if initial_pose is None else initial_pose,
                bounds=bounds or NavigationRuntimeBounds(),
                base_environment=os.environ,
            )
        self.context = context
        self.bounds = context.bounds
        self.processes: list[subprocess.Popen[str]] = []
        self.observations: dict[str, RuntimeObservation] = {}
        self.measurements: dict[str, Any] = {"started_at": now(), "processes": [], "readiness": [], "cleanup": {}}
        self.environment = context.environment
        self.log_dir = context.ros_log_dir
        self.log_files: list[Any] = []
        self._ready = False
        self.bootstrap_error: str | None = None
        self.readiness_result: NavigationReadinessResult | None = None
        self.initial_pose = context.initial_pose
        self.world_path = context.world_path

    @property
    def ready(self) -> bool:
        return self._ready

    def _start(self, name: str, command: list[str]) -> None:
        started = time.monotonic()
        log_path = Path(self.log_dir) / f"{name}.log"
        log_file = log_path.open("w+")
        self.log_files.append(log_file)
        process = subprocess.Popen(command, cwd=ROOT, text=True, stdout=log_file, stderr=subprocess.STDOUT, start_new_session=True, env=self.environment)
        self.processes.append(process)
        self.measurements["processes"].append({"name": name, "pid": process.pid, "pgid": os.getpgid(process.pid), "command": command, "log_path": str(log_path), "started_ms": round((time.monotonic() - started) * 1000, 3)})

    def start(self) -> None:
        # Nav2's integrated TB4 simulation launch owns the matching Gazebo
        # world, bridge, localization, and navigation topology.  Starting the
        # generic bringup separately leaves its map->odom transform unrelated
        # to the proxy robot and makes every goal fail closed.
        self._start("gazebo_nav2_proxy", [ROS2, "launch", "nav2_bringup", "tb4_simulation_launch.py", "headless:=True", "use_rviz:=False", "autostart:=False", f"x_pose:={self.initial_pose['x']}", f"y_pose:={self.initial_pose['y']}", f"yaw:={self.initial_pose['yaw']}", f"world:={self.world_path}"])
        deadline = time.monotonic() + self.bounds.startup_seconds
        while time.monotonic() < deadline:
            probe_start = time.monotonic()
            try:
                probe = subprocess.run([ROS2, "action", "list", "-t"], text=True, capture_output=True, timeout=3, check=False, env=self.environment)
            except subprocess.TimeoutExpired:
                self.measurements["readiness"].append({"command": [ROS2, "action", "list", "-t"], "timed_out": True, "duration_ms": round((time.monotonic() - probe_start) * 1000, 3)})
                if any(process.poll() is not None for process in self.processes):
                    return
                continue
            found = "/navigate_to_pose" in probe.stdout and "NavigateToPose" in probe.stdout
            self.measurements["readiness"].append({"command": [ROS2, "action", "list", "-t"], "returncode": probe.returncode, "navigate_to_pose": found, "duration_ms": round((time.monotonic() - probe_start) * 1000, 3)})
            if any(process.poll() is not None for process in self.processes):
                return
            try:
                map_server = subprocess.run([ROS2, "lifecycle", "get", "/map_server"], text=True, capture_output=True, timeout=3, check=False, env=self.environment)
            except subprocess.TimeoutExpired:
                map_server = None
            if map_server is not None and map_server.returncode == 0:
                return
            time.sleep(1)

    def _probe(self, label: str, command: list[str], timeout: float = 10) -> subprocess.CompletedProcess[str] | None:
        started = time.monotonic()
        try:
            result = subprocess.run(command, text=True, capture_output=True, timeout=timeout, check=False, env=self.environment)
            record: dict[str, Any] = {"label": label, "command": command, "returncode": result.returncode, "stdout": result.stdout[-1000:], "stderr": result.stderr[-1000:], "duration_ms": round((time.monotonic() - started) * 1000, 3), "timed_out": False}
        except subprocess.TimeoutExpired:
            result = None
            record = {"label": label, "command": command, "duration_ms": round((time.monotonic() - started) * 1000, 3), "timed_out": True}
        self.measurements.setdefault("localization", {}).setdefault("probes", []).append(record)
        return result

    def _probe_tf(self, label: str, target_frame: str, source_frame: str, timeout: float = 10) -> bool:
        """Bounded tf2_echo observation with explicit child reaping.

        tf2_echo streams transforms forever after success, so a zero exit status
        is neither expected nor required.
        """
        command = [ROS2, "run", "tf2_ros", "tf2_echo", target_frame, source_frame]
        started = time.monotonic()
        output = ""
        process: subprocess.Popen[str] | None = None
        timed_out = False
        try:
            process = subprocess.Popen(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, bufsize=1, env=self.environment)
            assert process.stdout is not None
            selector = selectors.DefaultSelector()
            selector.register(process.stdout, selectors.EVENT_READ)
            deadline = time.monotonic() + timeout
            while time.monotonic() < deadline:
                events = selector.select(min(0.2, deadline - time.monotonic()))
                for _, _ in events:
                    chunk = process.stdout.readline()
                    if chunk:
                        output += chunk
                        if transform_observed(output):
                            return True
                if process.poll() is not None:
                    break
            timed_out = process.poll() is None
            return False
        except OSError as exc:
            output += f"{type(exc).__name__}: {exc}"
            return False
        finally:
            if process is not None:
                if process.poll() is None:
                    process.terminate()
                    try:
                        process.wait(timeout=2)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait(timeout=2)
                self.measurements.setdefault("localization", {}).setdefault("probes", []).append({"label": label, "command": command, "target_frame": target_frame, "source_frame": source_frame, "duration_ms": round((time.monotonic() - started) * 1000, 3), "available": transform_observed(output), "observed_transform": transform_observed(output), "timed_out": timed_out, "output_tail": output[-1000:]})

    def _wait_for_tf(self, label: str, target_frame: str, source_frame: str, timeout: float) -> bool:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self._probe_tf(label, target_frame, source_frame, min(5, max(0.1, deadline - time.monotonic()))):
                return True
            time.sleep(min(1, max(0, deadline - time.monotonic())))
        return False

    def _wait_for_clock(self, timeout: float) -> bool:
        deadline = time.monotonic() + timeout
        localization = self.measurements.setdefault("localization", {})
        while time.monotonic() < deadline:
            result = self._probe(
                "simulation_clock",
                [ROS2, "topic", "echo", "--once", "/clock", "rosgraph_msgs/msg/Clock"],
                min(5, max(0.1, deadline - time.monotonic())),
            )
            available = result is not None and result.returncode == 0 and clock_observed(result.stdout)
            localization["clock_available"] = available
            if available:
                return True
            time.sleep(min(1, max(0, deadline - time.monotonic())))
        return False

    def _bootstrap_failed(self, reason: str) -> bool:
        self.bootstrap_error = reason
        self._ready = False
        localization = self.measurements.setdefault("localization", {})
        localization["failure"] = reason
        self.measurements["readiness"].append({"localization_ready": False, "reason": reason})
        return False

    @staticmethod
    def _readiness_stage(reason: str | None) -> str:
        """Map a concrete bootstrap failure to its first failed lifecycle stage."""
        if not reason:
            return "BOOTSTRAP"
        if "CLOCK" in reason:
            return "CLOCK"
        if reason.startswith(("ODOMETRY_", "LOCALIZATION_TOPICS_")):
            return "ODOM"
        if reason.startswith(("MAP_SERVER_", "AMCL_", "INITIAL_POSE_", "MAP_TO_ODOM_")):
            return "LOCALIZATION"
        if reason.startswith("SIM009_PRIVATE_ACTION_"):
            return "PRIVATE_ACTION"
        if reason.startswith(("NAVIGATION_LIFECYCLE_", "NAVIGATE_TO_POSE_")):
            return "ACTION"
        return "BOOTSTRAP"

    def establish_readiness(self) -> NavigationReadinessResult:
        """Run the one authoritative ENV→LAUNCH→CLOCK→ODOM→LOCALIZATION→ACTION path."""
        try:
            self.start()
        except Exception as exc:  # preserve the launch cause as structured data
            result = NavigationReadinessResult(
                False, "LAUNCH", f"{type(exc).__name__}: {exc}",
            )
        else:
            try:
                ready = self.bootstrap_localization()
            except Exception as exc:  # preserve the first bootstrap exception
                result = NavigationReadinessResult(
                    False, "BOOTSTRAP", f"{type(exc).__name__}: {exc}",
                )
            else:
                error = None if ready else (self.bootstrap_error or "NAVIGATION_BOOTSTRAP_FAILED")
                result = NavigationReadinessResult(
                    bool(ready), "READY" if ready else self._readiness_stage(error), error,
                )
        self.readiness_result = result
        self.measurements["session_readiness"] = result.as_dict()
        return result

    def bootstrap_localization(self) -> bool:
        """Activate localization, publish the documented spawn pose, prove map->odom."""
        self.bootstrap_error = None
        loc = self.measurements.setdefault("localization", {"initial_pose": dict(self.initial_pose)})
        if not self._wait_for_clock(self.bounds.localization_seconds):
            return self._bootstrap_failed("SIMULATION_CLOCK_UNAVAILABLE")
        topics = self._probe("localization_topics", [ROS2, "topic", "list", "-t"])
        if topics is None:
            return self._bootstrap_failed("LOCALIZATION_TOPICS_UNAVAILABLE")
        topic_text = topics.stdout
        loc["prerequisites"] = {"map_available": "/map" in topic_text, "scan_available": "/scan" in topic_text, "odom_available": "/odom" in topic_text}
        loc["prerequisites"]["odom_to_base_available"] = self._wait_for_tf("odom_to_base", "odom", "base_link", self.bounds.localization_seconds)
        if not all(loc["prerequisites"].values()):
            return self._bootstrap_failed("ODOMETRY_PREREQUISITES_UNAVAILABLE")
        for node in ("/map_server", "/amcl"):
            for transition in ("configure", "activate"):
                result = self._probe(f"{node}:{transition}", [ROS2, "lifecycle", "set", node, transition])
                if result is None or result.returncode != 0:
                    return self._bootstrap_failed(f"{node.removeprefix('/').upper()}_{transition.upper()}_FAILED")
        for node, key, label in (("/map_server", "map_server_active", "map_server_lifecycle"), ("/amcl", "amcl_active", "amcl_lifecycle")):
            result = self._probe(label, [ROS2, "lifecycle", "get", node])
            loc[key] = result is not None and lifecycle_is_active(result.stdout)
        if not loc["map_server_active"]:
            return self._bootstrap_failed("MAP_SERVER_NOT_ACTIVE")
        if not loc["amcl_active"]:
            return self._bootstrap_failed("AMCL_NOT_ACTIVE")
        pose = initial_pose_message(self.initial_pose)
        published = self._probe("initial_pose_publish", [ROS2, "topic", "pub", "--once", "/initialpose", "geometry_msgs/msg/PoseWithCovarianceStamped", pose], 5)
        loc["initial_pose"] = dict(self.initial_pose) | {"published": published is not None and published.returncode == 0}
        if not loc["initial_pose"]["published"]:
            return self._bootstrap_failed("INITIAL_POSE_PUBLISH_FAILED")
        loc["map_to_odom_available"] = self._wait_for_tf("map_to_odom", "map", "odom", self.bounds.localization_seconds)
        if not loc["initial_pose"]["published"] or not loc["map_to_odom_available"]:
            return self._bootstrap_failed("MAP_TO_ODOM_UNAVAILABLE")
        started = self._probe("navigation_lifecycle_start", [ROS2, "service", "call", "/lifecycle_manager_navigation/manage_nodes", "nav2_msgs/srv/ManageLifecycleNodes", "{command: 0}"], 10)
        if started is None or started.returncode != 0:
            return self._bootstrap_failed("NAVIGATION_LIFECYCLE_START_FAILED")
        deadline = time.monotonic() + self.bounds.localization_seconds
        while time.monotonic() < deadline:
            nav = self._probe("bt_navigator_lifecycle", [ROS2, "lifecycle", "get", "/bt_navigator"])
            actions = self._probe("navigate_to_pose_action", [ROS2, "action", "list", "-t"])
            active = nav is not None and lifecycle_is_active(nav.stdout)
            available = actions is not None and "/navigate_to_pose" in actions.stdout and "NavigateToPose" in actions.stdout
            self.measurements["readiness"].append({"bt_navigator_active": active, "navigate_to_pose": available})
            if active and available:
                self._ready = True
                return True
            time.sleep(1)
        return self._bootstrap_failed("NAVIGATE_TO_POSE_UNAVAILABLE")

    def navigate(self, request_data: dict[str, Any]) -> RuntimeObservation:
        action_id = request_data["action_id"]
        goal = GOALS[request_data["destination_id"]]
        started = time.monotonic()
        execution_bound = min(self.bounds.execution_seconds, max(0.001, int(request_data["timeout_ms"]) / 1000))
        try:
            completed = subprocess.run([ROS2, "action", "send_goal", "/navigate_to_pose", "nav2_msgs/action/NavigateToPose", goal], text=True, capture_output=True, timeout=execution_bound, check=False, env=self.environment)
        except subprocess.TimeoutExpired:
            observation = RuntimeObservation("unknown", error_code="NAVIGATION_TIMEOUT", error_message="NavigateToPose exceeded the bounded execution window", error_category="DEPENDENCY_TIMEOUT", retryable=True)
        else:
            output = completed.stdout + completed.stderr
            terminal_status = terminal_action_status(output)
            success = terminal_status == "SUCCEEDED"
            observation = RuntimeObservation("succeeded", arrival_verified=True) if success else RuntimeObservation("failed", error_code="NAVIGATION_ABORTED", error_message="NavigateToPose did not report a successful terminal status")
        self.observations[action_id] = observation
        self.measurements.setdefault("executions", []).append({"action_id": action_id, "destination_id": request_data["destination_id"], "goal": goal, "execution_bound_ms": round(execution_bound * 1000), "duration_ms": round((time.monotonic() - started) * 1000, 3), "returncode": None if 'completed' not in locals() else completed.returncode, "terminal_status": None if 'terminal_status' not in locals() else terminal_status, "stdout_tail": "" if 'completed' not in locals() else completed.stdout[-1000:], "stderr_tail": "" if 'completed' not in locals() else completed.stderr[-1000:], "observed_status": observation.observed_status, "arrival_verified": observation.arrival_verified})
        return observation

    def reconcile(self, action_id: str) -> RuntimeObservation:
        # The action CLI gives an authoritative terminal status before returning;
        # a bounded timeout remains unknown because no terminal status was read.
        return self.observations[action_id]

    def _owned_process_groups(self) -> set[int]:
        """Capture launch descendants before their parent can orphan them.

        ``ros2 launch`` commonly starts nodes in distinct process groups.  A
        top-level ``killpg`` alone therefore leaves those groups reparented and
        visible to the next bounded run.  The process table is sampled only
        while the launch owner is still alive, so unrelated host processes are
        never selected.
        """
        root_pids = {process.pid for process in self.processes if process.poll() is None}
        groups = {os.getpgid(pid) for pid in root_pids}
        if not root_pids:
            return groups
        try:
            table = subprocess.run(
                ["ps", "-eo", "pid=,ppid=,pgid="], text=True, capture_output=True,
                timeout=1, check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            return groups
        if table.returncode != 0:
            return groups
        rows: dict[int, tuple[int, int]] = {}
        for line in table.stdout.splitlines():
            try:
                pid, parent, group = (int(value) for value in line.split())
            except ValueError:
                continue
            rows[pid] = (parent, group)
        owned = set(root_pids)
        changed = True
        while changed:
            changed = False
            for pid, (parent, _group) in rows.items():
                if parent in owned and pid not in owned:
                    owned.add(pid)
                    changed = True
        groups.update(group for pid, (_parent, group) in rows.items() if pid in owned)
        return groups

    def close(self) -> bool:
        deadline = time.monotonic() + self.bounds.cleanup_seconds
        terminated: list[dict[str, Any]] = []
        owned_groups = self._owned_process_groups()
        for group in owned_groups:
            try:
                os.killpg(group, signal.SIGTERM)
            except ProcessLookupError:
                continue
        while time.monotonic() < deadline and any(process.poll() is None for process in self.processes):
            time.sleep(0.1)
        for process in self.processes:
            if process.poll() is None:
                for group in owned_groups:
                    try:
                        os.killpg(group, signal.SIGKILL)
                    except ProcessLookupError:
                        continue
            terminated.append({"pid": process.pid, "returncode": process.wait(timeout=2)})
        complete = all(process.poll() is not None for process in self.processes)
        for process, log_file in zip(self.processes, self.log_files):
            log_file.flush()
            log_file.seek(0)
            tail = log_file.read()[-2000:]
            self.measurements["processes"][self.processes.index(process)]["log_tail"] = tail
            log_file.close()
        self.measurements["cleanup"] = {"bound_ms": self.bounds.cleanup_seconds * 1000, "processes": terminated, "owned_process_groups": sorted(owned_groups), "complete": complete}
        return complete


def status_request(execute: dict[str, object]) -> dict[str, object]:
    return {key: execute[key] for key in ("schema_version", "mission_id", "trace_id", "timestamp", "deadline_at", "timeout_ms", "component_version", "action_id")} | {"operation": "action_status.get", "message_type": "request", "request_id": str(uuid.uuid4())}


def runtime_identity() -> dict[str, Any]:
    probes = {}
    for name, command in {"ros2": [ROS2, "--help"], "gazebo": ["gz", "sim", "--versions"], "nav2": [ROS2, "pkg", "prefix", "nav2_bringup"]}.items():
        started = time.monotonic()
        try:
            result = subprocess.run(command, text=True, capture_output=True, timeout=5, check=False)
            probes[name] = {"command": command, "returncode": result.returncode, "stdout": result.stdout[:1000], "stderr": result.stderr[:1000], "duration_ms": round((time.monotonic() - started) * 1000, 3)}
        except (OSError, subprocess.TimeoutExpired) as exc:
            probes[name] = {"command": command, "error": str(exc), "duration_ms": round((time.monotonic() - started) * 1000, 3)}
    return probes


def main() -> None:
    runtime = BoundedGazeboNav2Runtime()
    scenarios: list[dict[str, Any]] = []
    try:
        runtime.start()
        runtime.bootstrap_localization()
        backend = NavigationBackend(runtime)
        success = backend.execute(request())
        scenarios.append({"id": "success", "pass": success["result"] == "success" and success.get("arrival", {}).get("verified") is True, "result": success})
        invalid = backend.execute(request("raw-pose-forbidden"))
        scenarios.append({"id": "invalid_goal", "pass": invalid["result"] == "failure", "result": invalid})
        unavailable = NavigationBackend().execute(request())
        scenarios.append({"id": "unavailable", "pass": unavailable["result"] == "failure", "result": unavailable})
        blocked = backend.execute(request("blocked-bay"))
        scenarios.append({"id": "blocked", "pass": blocked["result"] != "success", "result": blocked})
        timed_request = request(timeout_ms=1)
        timed = backend.execute(timed_request)
        lookup = backend.action_status_get(status_request(timed_request))
        scenarios.append({"id": "timeout_reconciliation", "pass": timed["result"] == "pending" and timed["action_id"] == lookup["action_id"] and lookup["observed_status"] in {"unknown", "succeeded", "failed"}, "timeout": timed, "status": lookup})
    except Exception as exc:  # Evidence must retain the real runner failure.
        scenarios.append({"id": "runner", "pass": False, "error": f"{type(exc).__name__}: {exc}"})
    finally:
        cleanup_complete = runtime.close()

    baseline_path = ROOT / "results/simulation/SIM-003_baseline.json"
    acceptance_path = ROOT / "results/reviews/SIM-003_acceptance.json"
    passed = cleanup_complete and bool(scenarios) and all(item["pass"] for item in scenarios)
    payload = {"schema_version": "1.0", "task_id": "TASK-SIM-004", "generated_at": now(), "task_specific_result": "SIM_NAVIGATION_BACKEND_READY" if passed else "SIM_NAVIGATION_BACKEND_BLOCKED", "baseline_binding": {"path": str(baseline_path.relative_to(ROOT)), "sha256": hashlib.sha256(baseline_path.read_bytes()).hexdigest(), "acceptance_path": str(acceptance_path.relative_to(ROOT)), "acceptance_sha256": hashlib.sha256(acceptance_path.read_bytes()).hexdigest(), "baseline_id": "SIM_BASELINE_V1"}, "runtime_identity": runtime_identity(), "provenance": provenance(), "scenarios": scenarios, "bounded_lifecycle": runtime.measurements | {"startup_bound_ms": STARTUP_SECONDS * 1000, "execution_bound_ms": EXECUTION_SECONDS * 1000, "physical_device_dependency": False}}
    path = ROOT / "results/simulation/SIM-004_navigation_backend.json"
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(json.dumps(payload, sort_keys=True))


if __name__ == "__main__":
    main()
