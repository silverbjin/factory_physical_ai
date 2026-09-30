"""SIM-009 additive Nav2 goal tracking over the accepted SIM-004 runtime.

The public NavigationBackend remains protocol-only.  This adapter owns the
private Nav2 client goal handle and retains its UUID until the same goal's
terminal result has been observed or reconciliation remains unknown.
"""
from __future__ import annotations

import json
import select
import subprocess
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from scripts.run_simulation_navigation import BoundedGazeboNav2Runtime
from simulation_runtime.navigation_backend import RuntimeObservation


_GOAL_POINTS = {
    "warehouse-a": (-6.5, 0.0),
    "line-b-drop": (-6.0, 0.0),
    "blocked-bay": (100.0, 100.0),
}
_TIMEOUT_FAULT_SECONDS = 0.001
_CANCELLATION_RECONCILIATION_SECONDS = 2.0
_PRIVATE_ACTION_CLIENT_READY_SECONDS = 5.0
_ROS_PYTHON = "/usr/bin/python3"
_PRIVATE_ACTION_WORKER = Path(__file__).with_name("sim009_private_action_worker.py")


class PrivateActionWorker:
    """One bounded ROS-Python child using the immutable runtime environment."""

    def __init__(self, *, environment: Any, ros_domain_id: str) -> None:
        self.environment = environment
        self.ros_domain_id = ros_domain_id
        self.process = subprocess.Popen(
            [_ROS_PYTHON, str(_PRIVATE_ACTION_WORKER)],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, bufsize=1, env=environment, start_new_session=True,
        )

    def _request(self, payload: dict[str, Any], *, timeout: float = 6.0) -> dict[str, Any]:
        if self.process.poll() is not None or self.process.stdin is None or self.process.stdout is None:
            return {"error": "PRIVATE_ACTION_WORKER_NOT_RUNNING"}
        self.process.stdin.write(json.dumps(payload) + "\n")
        self.process.stdin.flush()
        try:
            readable, _, _ = select.select([self.process.stdout], [], [], timeout)
        except (OSError, TypeError, ValueError):  # StringIO controlled-test transport
            readable = [self.process.stdout]
        if not readable:
            return {"error": "PRIVATE_ACTION_WORKER_TIMEOUT"}
        line = self.process.stdout.readline()
        if not line:
            return {"error": "PRIVATE_ACTION_WORKER_EOF"}
        try:
            return json.loads(line)
        except json.JSONDecodeError:
            return {"error": "PRIVATE_ACTION_WORKER_PROTOCOL_MALFORMED"}

    def ready(self) -> bool:
        response = self._request({"operation": "ready", "domain_id": int(self.ros_domain_id)})
        return response.get("ready") is True

    def execute(self, request: dict[str, Any]) -> dict[str, Any]:
        return self._request({"operation": "execute", **request}, timeout=max(8.0, float(request["timeout_seconds"]) + 5.0))

    def reconcile(self, action_id: str) -> dict[str, Any]:
        return self._request({"operation": "reconcile", "action_id": action_id}, timeout=6.0)

    def close(self) -> None:
        if self.process.poll() is None:
            self._request({"operation": "close"}, timeout=2.0)
            try:
                self.process.wait(timeout=2.0)
            except subprocess.TimeoutExpired:
                self.process.terminate()
                try:
                    self.process.wait(timeout=2.0)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                    self.process.wait(timeout=2.0)


@dataclass(slots=True)
class ScenarioExecution:
    scenario_id: str
    scenario_execution_id: str
    fault_arm_event: dict[str, str] | None = None


@dataclass(slots=True)
class TFProbeRecord:
    scenario_id: str
    scenario_execution_id: str
    label: str
    target_frame: str
    source_frame: str
    available: bool


@dataclass(slots=True)
class GoalAttemptRecord:
    """One logical navigation attempt and the exact Nav2 goal it created."""

    mission_id: str
    action_id: str
    idempotency_key: str
    destination_id: str
    nav2_goal_uuid: str
    scenario_id: str = ""
    scenario_execution_id: str = ""
    injection_kind: str = "none"
    frame_id: str = "map"
    behavior_tree: str = ""
    native_error_code: str | None = None
    native_error_message: str | None = None
    server_log_tail: str = ""
    server_log_attributed: bool = False
    server_log_start_offsets: dict[str, int] = field(default_factory=dict)
    server_log_end_offsets: dict[str, int] = field(default_factory=dict)
    terminal_goal_uuid: str | None = None
    terminal_status: str | None = None
    goal_handle: Any = field(default=None, repr=False)
    result_future: Any = field(default=None, repr=False)
    timeout_fault: bool = False
    cancellation_requested: bool = False
    retryable_terminal_failure: bool = False
    terminal_observation: RuntimeObservation | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        # A terminal result, when it arrives, is required to carry this exact
        # client goal identity.  The field is initialized now so evidence can
        # make the binding explicit even while the status is still pending.
        if self.terminal_goal_uuid is None:
            self.terminal_goal_uuid = self.nav2_goal_uuid


class GoalTrackedGazeboNav2Runtime(BoundedGazeboNav2Runtime):
    """BoundedGazeboNav2Runtime with real Nav2 ClientGoalHandle identity."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        # An action_id is stable across a retry, so it cannot itself be the
        # attempt key.  Retain every Nav2 UUID for the logical effect and use
        # the separate index only to reconcile the currently active attempt.
        self.goal_attempts: list[GoalAttemptRecord] = []
        self._attempts_by_action_id: dict[str, GoalAttemptRecord] = {}
        self._node: Any = None
        self._action_client: Any = None
        self._rclpy: Any = None
        self._rclpy_context: Any = None
        self._private_worker: PrivateActionWorker | None = None
        self._next_goal_timeout_fault_seconds: float | None = None
        self._next_goal_fault: dict[str, str] | None = None
        self._active_scenario: ScenarioExecution | None = None
        self._scenario_contexts: dict[str, ScenarioExecution] = {}
        self._tf_probe_records: list[TFProbeRecord] = []

    def begin_scenario(
        self, scenario_id: str, scenario_execution_id: str | None = None,
    ) -> ScenarioExecution:
        if getattr(self, "_active_scenario", None) is not None:
            raise RuntimeError("SIM-009 navigation scenario context is already active")
        context = ScenarioExecution(scenario_id, scenario_execution_id or str(uuid.uuid4()))
        self._active_scenario = context
        if not hasattr(self, "_scenario_contexts"):
            self._scenario_contexts = {}
        self._scenario_contexts[context.scenario_execution_id] = context
        return context

    def end_scenario(self, context: ScenarioExecution) -> None:
        if getattr(self, "_active_scenario", None) is not context:
            raise RuntimeError("SIM-009 navigation scenario context mismatch")
        self._active_scenario = None
        self._next_goal_fault = None

    def _require_scenario(self) -> ScenarioExecution:
        if getattr(self, "_active_scenario", None) is None:
            raise RuntimeError("SIM-009 live navigation requires a scenario execution context")
        return self._active_scenario

    def inject_timeout_on_next_goal(self) -> None:
        """Cause the next accepted goal to time out before its result is read."""
        self._next_goal_timeout_fault_seconds = _TIMEOUT_FAULT_SECONDS

    def inject_abort_on_next_goal(self) -> None:
        """Arm a private, one-shot Nav2 behavior-tree load failure."""
        self._next_goal_fault = {
            "injection_kind": "missing_behavior_tree",
            "behavior_tree": "/tmp/sim009-missing-behavior-tree.xml",
            "frame_id": "map",
        }
        self._require_scenario().fault_arm_event = dict(self._next_goal_fault)

    def inject_tf_unavailable_on_next_goal(self) -> None:
        """Arm a private, one-shot goal frame that Nav2 cannot transform."""
        context = self._require_scenario()
        self._next_goal_fault = {
            "injection_kind": "missing_goal_frame",
            "behavior_tree": "",
            "frame_id": f"sim009_missing_tf_frame_{context.scenario_execution_id}",
        }
        context.fault_arm_event = dict(self._next_goal_fault)

    def _record_attempt(self, attempt: GoalAttemptRecord) -> None:
        """Retain each Nav2 UUID while indexing the latest attempt to reconcile."""
        context = self._require_scenario()
        if not attempt.scenario_id:
            attempt.scenario_id = context.scenario_id
        if not attempt.scenario_execution_id:
            attempt.scenario_execution_id = context.scenario_execution_id
        if attempt.scenario_id != context.scenario_id or attempt.scenario_execution_id != context.scenario_execution_id:
            raise RuntimeError("SIM-009 goal attempt context mismatch")
        self.goal_attempts.append(attempt)
        self._attempts_by_action_id[attempt.action_id] = attempt

    def _record_tf_probe(
        self, label: str, target_frame: str, source_frame: str, available: bool,
    ) -> None:
        context = self._require_scenario()
        self._tf_probe_records.append(TFProbeRecord(
            context.scenario_id, context.scenario_execution_id, label,
            target_frame, source_frame, available,
        ))

    def _probe_scenario_tf(self, label: str, target_frame: str, source_frame: str) -> bool:
        available = self._probe_tf(label, target_frame, source_frame, 5.0)
        self._record_tf_probe(label, target_frame, source_frame, available)
        return available

    def _process_log_paths(self) -> list[Path]:
        """Return the accepted runtime's process logs without owning them."""
        paths: list[Path] = []
        for process in self.measurements.get("processes", []):
            log_path = process.get("log_path")
            if isinstance(log_path, str):
                paths.append(Path(log_path))
        return paths

    def _capture_log_offsets(self) -> dict[str, int] | None:
        """Snapshot every accepted process log before a single Nav2 goal."""
        for log_file in getattr(self, "log_files", []):
            log_file.flush()
        paths = self._process_log_paths()
        if not paths:
            return None
        offsets: dict[str, int] = {}
        try:
            for path in paths:
                offsets[str(path)] = path.stat().st_size
        except OSError:
            return None
        return offsets

    def _read_server_log_window(
        self, start_offsets: dict[str, int] | None,
    ) -> tuple[str, bool, dict[str, int]]:
        """Read only bytes written after a goal's own start snapshot.

        A missing/truncated log never falls back to the cumulative process tail:
        the resulting Evidence is explicitly unattributed and fails closed.
        """
        if not start_offsets:
            return "", False, {}
        for log_file in getattr(self, "log_files", []):
            log_file.flush()
        chunks: list[str] = []
        end_offsets: dict[str, int] = {}
        try:
            for raw_path, start in start_offsets.items():
                path = Path(raw_path)
                end = path.stat().st_size
                if end < start:
                    return "", False, {}
                with path.open("rb") as log_file:
                    log_file.seek(start)
                    chunks.append(log_file.read(end - start).decode("utf-8", errors="replace"))
                end_offsets[raw_path] = end
        except OSError:
            return "", False, {}
        return "\n".join(chunks), True, end_offsets

    def _preflight_private_action_client(self) -> bool:
        """Bound private DDS discovery before any scenario timer starts."""
        if getattr(self, "_private_worker", None) is None:
            self._private_worker = PrivateActionWorker(
                environment=self.environment,
                ros_domain_id=self.context.ros_domain_id,
            )
        available = self._private_worker.ready()
        self.measurements.setdefault("readiness", []).append({
            "sim009_private_action_client": available,
            "timeout_seconds": _PRIVATE_ACTION_CLIENT_READY_SECONDS,
        })
        return available

    def bootstrap_localization(self) -> bool:
        """Keep the accepted bootstrap, then ready SIM-009's private client."""
        if not super().bootstrap_localization():
            return False
        self._ready = self._preflight_private_action_client()
        if not self._ready:
            return self._bootstrap_failed("SIM009_PRIVATE_ACTION_CLIENT_UNAVAILABLE")
        return self._ready

    def _client(self) -> tuple[Any, Any, Any, Any] | None:
        if self._action_client is not None:
            return self._rclpy, self._node, self._action_client, self._goal_type
        try:
            import rclpy
            from geometry_msgs.msg import PoseStamped
            from nav2_msgs.action import NavigateToPose
            from rclpy.action import ActionClient
        except ImportError:
            return None
        # Use an explicit private rclpy context in the same domain as the
        # immutable runtime context.  Never mutate process-global ROS state.
        context = rclpy.context.Context()
        rclpy.init(args=None, context=context, domain_id=int(self.context.ros_domain_id))
        node = rclpy.create_node("sim009_goal_tracker", context=context)
        client = ActionClient(node, NavigateToPose, "/navigate_to_pose")
        self._rclpy, self._node, self._action_client = rclpy, node, client
        self._rclpy_context = context
        self._goal_type = (NavigateToPose, PoseStamped)
        return rclpy, node, client, self._goal_type

    @staticmethod
    def _uuid(goal_handle: Any) -> str:
        return str(uuid.UUID(bytes=bytes(goal_handle.goal_id.uuid)))

    def _observation_from_result(self, attempt: GoalAttemptRecord) -> RuntimeObservation:
        result = attempt.result_future.result()
        status = result.status
        attempt.terminal_status = str(status)
        native_result = getattr(result, "result", None)
        attempt.native_error_code = str(getattr(native_result, "error_code", "")) or None
        attempt.native_error_message = str(getattr(native_result, "error_msg", "")) or None
        (
            attempt.server_log_tail,
            attempt.server_log_attributed,
            attempt.server_log_end_offsets,
        ) = self._read_server_log_window(attempt.server_log_start_offsets)
        # nav2_msgs/action status codes: SUCCEEDED=4.  The result future is
        # attached to the same ClientGoalHandle, not a second lookup goal.
        if status == 4 and attempt.injection_kind != "none":
            return RuntimeObservation(
                "failed", error_code="SIM009_FAULT_NOT_OBSERVED",
                error_message="fault-injected Nav2 goal unexpectedly succeeded",
                error_category="EXECUTION_FAILED",
            )
        if status == 4:
            return RuntimeObservation("succeeded", arrival_verified=True)
        if attempt.injection_kind == "missing_goal_frame":
            error_code = "NAVIGATION_TF_UNAVAILABLE"
        elif attempt.injection_kind == "missing_behavior_tree":
            error_code = "NAVIGATION_ABORTED"
        else:
            error_code = "NAVIGATION_ABORTED"
        native_detail = " ".join(
            item for item in (attempt.native_error_code, attempt.native_error_message) if item
        )
        return RuntimeObservation(
            "failed", error_code=error_code,
            error_message=(native_detail or f"Nav2 terminal goal status {status}"),
            retryable=attempt.retryable_terminal_failure,
        )

    def _observation_from_worker(
        self, attempt: GoalAttemptRecord, response: dict[str, Any],
    ) -> RuntimeObservation:
        """Normalize the ROS-worker's same-goal terminal response."""
        # A worker response is authoritative only when it names the exact
        # goal the parent recorded for this action.  Do not let a terminal
        # observation from a different worker-side goal acquire this goal's
        # log boundary.
        if str(response.get("goal_uuid", "")) != attempt.nav2_goal_uuid:
            return RuntimeObservation(
                "failed", error_code="NAV2_GOAL_IDENTITY_MISMATCH",
                error_message="private action worker terminal identity differs from dispatched goal",
                error_category="INTERNAL",
            )
        attempt.terminal_status = str(response["terminal_status"])
        attempt.native_error_code = response.get("native_error_code")
        attempt.native_error_message = response.get("native_error_message")
        (
            attempt.server_log_tail,
            attempt.server_log_attributed,
            attempt.server_log_end_offsets,
        ) = self._read_server_log_window(attempt.server_log_start_offsets)
        if attempt.terminal_status == "4" and attempt.injection_kind != "none":
            observation = RuntimeObservation(
                "failed", error_code="SIM009_FAULT_NOT_OBSERVED",
                error_message="fault-injected Nav2 goal unexpectedly succeeded",
                error_category="EXECUTION_FAILED",
            )
        elif attempt.terminal_status == "4":
            observation = RuntimeObservation("succeeded", arrival_verified=True)
        else:
            error_code = (
                "NAVIGATION_TF_UNAVAILABLE"
                if attempt.injection_kind == "missing_goal_frame"
                else "NAVIGATION_ABORTED"
            )
            native_detail = " ".join(
                item for item in (attempt.native_error_code, attempt.native_error_message) if item
            )
            observation = RuntimeObservation(
                "failed", error_code=error_code,
                error_message=(native_detail or f"Nav2 terminal goal status {attempt.terminal_status}"),
                retryable=attempt.retryable_terminal_failure,
            )
        attempt.terminal_observation = observation
        return observation

    def _navigate_with_worker(
        self, request: dict[str, Any], context: ScenarioExecution,
    ) -> RuntimeObservation:
        fault = self._next_goal_fault
        self._next_goal_fault = None
        timeout_fault = self._next_goal_timeout_fault_seconds is not None
        self._next_goal_timeout_fault_seconds = None
        if fault and fault["injection_kind"] == "missing_goal_frame":
            self._probe_scenario_tf("sim009_tf_baseline", "map", "base_link")
            self._probe_scenario_tf("sim009_tf_injected_missing", fault["frame_id"], "base_link")
        x, y = _GOAL_POINTS[request["destination_id"]]
        # This parent owns the launch logs.  Snapshot them immediately before
        # sending the worker request, then read only that same window after
        # the worker has observed this goal's terminal result.
        log_start_offsets = self._capture_log_offsets()
        response = self._private_worker.execute({
            "action_id": request["action_id"], "x": x, "y": y,
            "frame_id": fault["frame_id"] if fault else "map",
            "behavior_tree": fault["behavior_tree"] if fault else "",
            "timeout_seconds": max(0.001, min(30.0, request["timeout_ms"] / 1000)),
            "timeout_fault": timeout_fault,
        })
        if response.get("state") == "unavailable":
            return RuntimeObservation("failed", error_code="NAV2_ACTION_UNAVAILABLE", error_message="NavigateToPose action server is unavailable", error_category="RESOURCE_UNAVAILABLE")
        if response.get("state") == "rejected":
            return RuntimeObservation("failed", error_code="NAVIGATION_REJECTED", error_message="Nav2 rejected the requested goal")
        if "error" in response or "goal_uuid" not in response:
            return RuntimeObservation("failed", error_code="NAV2_CLIENT_UNAVAILABLE", error_message=str(response.get("error", "private action worker produced no goal identity")), error_category="RESOURCE_UNAVAILABLE")
        attempt = GoalAttemptRecord(
            mission_id=request["mission_id"], action_id=request["action_id"],
            idempotency_key=request["idempotency_key"], destination_id=request["destination_id"],
            nav2_goal_uuid=str(response["goal_uuid"]), scenario_id=context.scenario_id,
            scenario_execution_id=context.scenario_execution_id,
            injection_kind=fault["injection_kind"] if fault else "none",
            frame_id=fault["frame_id"] if fault else "map",
            behavior_tree=fault["behavior_tree"] if fault else "",
            server_log_start_offsets=log_start_offsets or {},
            timeout_fault=timeout_fault,
        )
        self._record_attempt(attempt)
        if response.get("state") == "pending":
            return RuntimeObservation("unknown", error_code="NAVIGATION_TIMEOUT", error_message="same Nav2 goal exceeded the bounded execution window", error_category="DEPENDENCY_TIMEOUT", retryable=True)
        if response.get("state") == "terminal":
            return self._observation_from_worker(attempt, response)
        return RuntimeObservation("failed", error_code="NAV2_CLIENT_UNAVAILABLE", error_message="private action worker returned an unknown state", error_category="RESOURCE_UNAVAILABLE")

    def _reconcile_timeout_attempt(self, attempt: GoalAttemptRecord) -> RuntimeObservation:
        """Cancel the timed-out ClientGoalHandle and read its terminal result."""
        attempt.cancellation_requested = True
        cancellation = attempt.goal_handle.cancel_goal_async()
        self._rclpy.spin_until_future_complete(
            self._node, cancellation, timeout_sec=_CANCELLATION_RECONCILIATION_SECONDS,
        )
        if not cancellation.done():
            return RuntimeObservation(
                "unknown", error_code="NAVIGATION_CANCELLATION_PENDING",
                error_message="same Nav2 goal cancellation has no authoritative response",
                error_category="DEPENDENCY_TIMEOUT", retryable=False,
            )
        self._rclpy.spin_until_future_complete(
            self._node, attempt.result_future, timeout_sec=_CANCELLATION_RECONCILIATION_SECONDS,
        )
        if not attempt.result_future.done():
            return RuntimeObservation(
                "unknown", error_code="NAVIGATION_RECONCILIATION_PENDING",
                error_message="same cancelled Nav2 goal has no terminal result",
                error_category="DEPENDENCY_TIMEOUT", retryable=False,
            )
        terminal_status = attempt.result_future.result().status
        attempt.retryable_terminal_failure = terminal_status in {5, 6}
        return self._observation_from_result(attempt)

    def navigate(self, request: dict[str, Any]) -> RuntimeObservation:
        try:
            context = self._require_scenario()
        except RuntimeError as exc:
            return RuntimeObservation(
                "failed", error_code="SIM009_SCENARIO_CONTEXT_MISSING",
                error_message=str(exc), error_category="INTERNAL",
            )
        if getattr(self, "_private_worker", None) is not None:
            return self._navigate_with_worker(request, context)
        client_parts = self._client()
        if client_parts is None:
            return RuntimeObservation("failed", error_code="NAV2_CLIENT_UNAVAILABLE", error_message="rclpy/Nav2 client is unavailable", error_category="RESOURCE_UNAVAILABLE")
        rclpy, node, client, (goal_type, pose_type) = client_parts
        timeout = max(0.001, min(30.0, request["timeout_ms"] / 1000))
        if not client.wait_for_server(timeout_sec=timeout):
            return RuntimeObservation("failed", error_code="NAV2_ACTION_UNAVAILABLE", error_message="NavigateToPose action server is unavailable", error_category="RESOURCE_UNAVAILABLE")
        fault = self._next_goal_fault
        self._next_goal_fault = None
        x, y = _GOAL_POINTS[request["destination_id"]]
        goal = goal_type.Goal()
        goal.pose = pose_type()
        goal.pose.header.frame_id = fault["frame_id"] if fault else "map"
        goal.pose.pose.position.x, goal.pose.pose.position.y = x, y
        goal.pose.pose.orientation.w = 1.0
        if fault and fault["behavior_tree"]:
            goal.behavior_tree = fault["behavior_tree"]
        if fault and fault["injection_kind"] == "missing_goal_frame":
            self._probe_scenario_tf("sim009_tf_baseline", "map", "base_link")
            self._probe_scenario_tf("sim009_tf_injected_missing", fault["frame_id"], "base_link")
        log_start_offsets = self._capture_log_offsets()
        sent = client.send_goal_async(goal)
        rclpy.spin_until_future_complete(node, sent, timeout_sec=timeout)
        if not sent.done() or not sent.result().accepted:
            return RuntimeObservation("failed", error_code="NAVIGATION_REJECTED", error_message="Nav2 rejected the requested goal")
        handle = sent.result()
        timeout_fault = self._next_goal_timeout_fault_seconds
        self._next_goal_timeout_fault_seconds = None
        attempt = GoalAttemptRecord(
            mission_id=request["mission_id"], action_id=request["action_id"],
            idempotency_key=request["idempotency_key"], destination_id=request["destination_id"],
            nav2_goal_uuid=self._uuid(handle), goal_handle=handle,
            result_future=handle.get_result_async(), timeout_fault=timeout_fault is not None,
            scenario_id=context.scenario_id,
            scenario_execution_id=context.scenario_execution_id,
            injection_kind=fault["injection_kind"] if fault else "none",
            frame_id=fault["frame_id"] if fault else "map",
            behavior_tree=fault["behavior_tree"] if fault else "",
            server_log_start_offsets=log_start_offsets or {},
        )
        self._record_attempt(attempt)
        execution_timeout = timeout_fault if timeout_fault is not None else timeout
        rclpy.spin_until_future_complete(node, attempt.result_future, timeout_sec=execution_timeout)
        if not attempt.result_future.done():
            return RuntimeObservation("unknown", error_code="NAVIGATION_TIMEOUT", error_message="same Nav2 goal exceeded its bounded execution window", error_category="DEPENDENCY_TIMEOUT", retryable=True)
        return self._observation_from_result(attempt)

    def reconcile(self, action_id: str) -> RuntimeObservation:
        attempt = self._attempts_by_action_id[action_id]
        if getattr(self, "_private_worker", None) is not None:
            if attempt.terminal_observation is not None:
                return attempt.terminal_observation
            if attempt.timeout_fault:
                attempt.cancellation_requested = True
            response = self._private_worker.reconcile(action_id)
            if response.get("state") == "terminal":
                attempt.retryable_terminal_failure = str(response["terminal_status"]) in {"5", "6"}
                return self._observation_from_worker(attempt, response)
            return RuntimeObservation(
                "unknown", error_code="NAVIGATION_RECONCILIATION_PENDING",
                error_message="same cancelled Nav2 goal has no terminal result",
                error_category="DEPENDENCY_TIMEOUT", retryable=False,
            )
        if not attempt.result_future.done():
            if attempt.timeout_fault:
                return self._reconcile_timeout_attempt(attempt)
            self._rclpy.spin_until_future_complete(self._node, attempt.result_future, timeout_sec=5.0)
        if not attempt.result_future.done():
            return RuntimeObservation("unknown", error_code="NAVIGATION_RECONCILIATION_PENDING", error_message="same Nav2 goal has no terminal result", error_category="DEPENDENCY_TIMEOUT", retryable=False)
        return self._observation_from_result(attempt)

    def evidence_for(self, scenario_execution_id: str) -> dict[str, Any]:
        attempts = [item for item in self.goal_attempts if item.scenario_execution_id == scenario_execution_id]
        contexts = {item.scenario_id for item in attempts}
        context = getattr(self, "_scenario_contexts", {}).get(scenario_execution_id)
        probes = [item for item in self._tf_probe_records if item.scenario_execution_id == scenario_execution_id]
        if len(contexts) > 1:
            raise RuntimeError("SIM-009 scenario Evidence contains mixed scenario IDs")
        return {
            "goal_attempts": [
                {"mission_id": item.mission_id, "action_id": item.action_id,
                 "idempotency_key": item.idempotency_key, "destination_id": item.destination_id,
                 "nav2_goal_uuid": item.nav2_goal_uuid, "terminal_goal_uuid": item.terminal_goal_uuid,
                 "terminal_status": item.terminal_status, "timeout_fault": item.timeout_fault,
                 "cancellation_requested": item.cancellation_requested,
                 "retryable_terminal_failure": item.retryable_terminal_failure,
                 "scenario_id": item.scenario_id, "injection_kind": item.injection_kind,
                 "scenario_execution_id": item.scenario_execution_id,
                 "frame_id": item.frame_id, "behavior_tree": item.behavior_tree,
                 "native_error_code": item.native_error_code,
                 "native_error_message": item.native_error_message,
                 "server_log_tail": item.server_log_tail,
                 "server_log_attributed": item.server_log_attributed,
                 "server_log_start_offsets": dict(item.server_log_start_offsets),
                 "server_log_end_offsets": dict(item.server_log_end_offsets)}
                for item in attempts
            ],
            "scenario_id": next(iter(contexts), context.scenario_id if context else None),
            "scenario_execution_id": scenario_execution_id,
            "fault_arm_event": dict(context.fault_arm_event) if context and context.fault_arm_event else None,
            "cleanup": self.measurements.get("cleanup", {}),
            "tf_probes": [
                {"scenario_id": item.scenario_id, "scenario_execution_id": item.scenario_execution_id,
                 "label": item.label, "target_frame": item.target_frame,
                 "source_frame": item.source_frame, "available": item.available}
                for item in probes
            ],
            "runtime_calls": len(attempts),
            "logical_side_effect_count": len({
                item.action_id for item in attempts if item.terminal_status == "4"
            }),
        }

    def evidence(self, scenario_id: str | None = None) -> dict[str, Any]:
        """Compatibility accessor; live scenario rows must use ``evidence_for``."""
        if scenario_id is not None:
            raise RuntimeError("SIM-009 Evidence must be selected by scenario_execution_id")
        return {"goal_attempts": [], "scenario_id": None, "scenario_execution_id": None,
                "cleanup": self.measurements.get("cleanup", {}), "tf_probes": []}

    def close(self) -> bool:
        if self._private_worker is not None:
            self._private_worker.close()
            self._private_worker = None
        if self._node is not None:
            self._node.destroy_node()
            self._rclpy.shutdown(context=self._rclpy_context)
            self._node = self._action_client = self._rclpy = None
            self._rclpy_context = None
        return super().close()
