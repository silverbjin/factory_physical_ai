#!/usr/bin/env python3
"""Run SIM-004 against a bounded Gazebo Harmonic + ROS 2 + Nav2 process set.

The runner is intentionally fail-closed: it writes BLOCKED evidence whenever a
real process cannot become ready, a scenario cannot be observed, or cleanup is
not verified.  It never substitutes an in-memory success for a runtime result.
"""
from __future__ import annotations

import hashlib
import json
import os
import selectors
import signal
import subprocess
import sys
import tempfile
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from simulation_runtime.navigation_backend import (  # noqa: E402
    NavigationBackend, RuntimeObservation, provenance,
)

ROS2 = "/opt/ros/jazzy/bin/ros2"
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


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def lifecycle_is_active(output: str) -> bool:
    """Only Nav2's canonical active lifecycle state is readiness proof."""
    return "active [3]" in output.lower()


def transform_observed(output: str) -> bool:
    """Recognize tf2_echo's emitted transform, not its intentionally open lifetime."""
    normalized = output.lower()
    return "at time" in normalized and "translation:" in normalized and "rotation:" in normalized


def terminal_action_status(output: str) -> str | None:
    for status in ("SUCCEEDED", "ABORTED", "CANCELED"):
        if f"Goal finished with status: {status}" in output:
            return status
    return None


def request(destination: str = "line-b-drop", timeout_ms: int = 30000) -> dict[str, object]:
    stamp = datetime.now(timezone.utc)
    return {"operation": "navigation.execute", "message_type": "request", "schema_version": "1.0", "mission_id": str(uuid.uuid4()), "request_id": str(uuid.uuid4()), "trace_id": str(uuid.uuid4()), "idempotency_key": "sim004-navigation", "action_id": str(uuid.uuid4()), "timestamp": stamp.isoformat().replace("+00:00", "Z"), "deadline_at": (stamp + timedelta(milliseconds=timeout_ms)).isoformat().replace("+00:00", "Z"), "timeout_ms": timeout_ms, "component_version": "sim004-runner-v2", "attempt": 1, "retry_budget_remaining": 1, "robot_id": "simulation-proxy-mobile-base", "destination_id": destination, "speed_profile_id": "sim-safe-v1"}


class BoundedGazeboNav2Runtime:
    """Private ROS action implementation with process-group lifecycle control."""

    def __init__(self) -> None:
        self.processes: list[subprocess.Popen[str]] = []
        self.observations: dict[str, RuntimeObservation] = {}
        self.measurements: dict[str, Any] = {"started_at": now(), "processes": [], "readiness": [], "cleanup": {}}
        self.environment = os.environ.copy()
        # Codex workers cannot write the user's home directory.  ROS launch
        # logs are task-local temporary runtime output, not Evidence inputs.
        self.log_dir = tempfile.mkdtemp(prefix="sim004-ros-", dir="/tmp")
        self.environment["ROS_LOG_DIR"] = self.log_dir
        # Isolate DDS and Gazebo transport from prior/manual runs.
        self.environment["ROS_DOMAIN_ID"] = "44"
        self.environment["GZ_PARTITION"] = f"sim004-{uuid.uuid4().hex[:12]}"
        self.log_files: list[Any] = []
        self._ready = False

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
        self._start("gazebo_nav2_proxy", [ROS2, "launch", "nav2_bringup", "tb4_simulation_launch.py", "headless:=True", "use_rviz:=False", "autostart:=False", f"x_pose:={CANONICAL_START['x']}", f"y_pose:={CANONICAL_START['y']}", f"yaw:={CANONICAL_START['yaw']}", f"world:={ROOT / 'data/simulation/sim004_navigation_proxy_world.sdf'}"])
        deadline = time.monotonic() + STARTUP_SECONDS
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

    def bootstrap_localization(self) -> bool:
        """Activate localization, publish the documented spawn pose, prove map->odom."""
        loc = self.measurements.setdefault("localization", {"initial_pose": CANONICAL_START})
        for node in ("/map_server", "/amcl"):
            for transition in ("configure", "activate"):
                result = self._probe(f"{node}:{transition}", [ROS2, "lifecycle", "set", node, transition])
                if result is None or result.returncode != 0:
                    return False
        topics = self._probe("localization_topics", [ROS2, "topic", "list", "-t"])
        if topics is None:
            return False
        topic_text = topics.stdout
        loc["prerequisites"] = {"map_available": "/map" in topic_text, "scan_available": "/scan" in topic_text, "odom_available": "/odom" in topic_text}
        amcl = self._probe("amcl_lifecycle", [ROS2, "lifecycle", "get", "/amcl"])
        loc["amcl_active"] = amcl is not None and lifecycle_is_active(amcl.stdout)
        loc["prerequisites"]["odom_to_base_available"] = self._probe_tf("odom_to_base", "odom", "base_link")
        if not loc["amcl_active"] or not all(loc["prerequisites"].values()):
            return False
        pose = f"{{header: {{frame_id: map}}, pose: {{pose: {{position: {{x: {CANONICAL_START['x']}, y: {CANONICAL_START['y']}, z: 0.0}}, orientation: {{z: 0.0, w: 1.0}}}}, covariance: [0.25, 0, 0, 0, 0, 0, 0, 0.25, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]}}}}"
        published = self._probe("initial_pose_publish", [ROS2, "topic", "pub", "--once", "/initialpose", "geometry_msgs/msg/PoseWithCovarianceStamped", pose], 5)
        loc["initial_pose"] = CANONICAL_START | {"published": published is not None and published.returncode == 0}
        loc["map_to_odom_available"] = self._probe_tf("map_to_odom", "map", "odom", 5)
        if not loc["initial_pose"]["published"] or not loc["map_to_odom_available"]:
            return False
        started = self._probe("navigation_lifecycle_start", [ROS2, "service", "call", "/lifecycle_manager_navigation/manage_nodes", "nav2_msgs/srv/ManageLifecycleNodes", "{command: 0}"], 10)
        if started is None or started.returncode != 0:
            return False
        deadline = time.monotonic() + LOCALIZATION_SECONDS
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
        return False

    def navigate(self, request_data: dict[str, Any]) -> RuntimeObservation:
        action_id = request_data["action_id"]
        goal = GOALS[request_data["destination_id"]]
        started = time.monotonic()
        execution_bound = min(EXECUTION_SECONDS, max(0.001, int(request_data["timeout_ms"]) / 1000))
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

    def close(self) -> bool:
        deadline = time.monotonic() + CLEANUP_SECONDS
        terminated: list[dict[str, Any]] = []
        for process in self.processes:
            if process.poll() is None:
                os.killpg(os.getpgid(process.pid), signal.SIGTERM)
        while time.monotonic() < deadline and any(process.poll() is None for process in self.processes):
            time.sleep(0.1)
        for process in self.processes:
            if process.poll() is None:
                os.killpg(os.getpgid(process.pid), signal.SIGKILL)
            terminated.append({"pid": process.pid, "returncode": process.wait(timeout=2)})
        complete = all(process.poll() is not None for process in self.processes)
        for process, log_file in zip(self.processes, self.log_files):
            log_file.flush()
            log_file.seek(0)
            tail = log_file.read()[-2000:]
            self.measurements["processes"][self.processes.index(process)]["log_tail"] = tail
            log_file.close()
        self.measurements["cleanup"] = {"bound_ms": CLEANUP_SECONDS * 1000, "processes": terminated, "complete": complete}
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
