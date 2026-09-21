"""SIM-009 additive Nav2 goal tracking over the accepted SIM-004 runtime.

The public NavigationBackend remains protocol-only.  This adapter owns the
private Nav2 client goal handle and retains its UUID until the same goal's
terminal result has been observed or reconciliation remains unknown.
"""
from __future__ import annotations

import os
import time
import uuid
from dataclasses import dataclass, field
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


@dataclass(slots=True)
class GoalAttemptRecord:
    """One logical navigation attempt and the exact Nav2 goal it created."""

    mission_id: str
    action_id: str
    idempotency_key: str
    destination_id: str
    nav2_goal_uuid: str
    terminal_goal_uuid: str | None = None
    terminal_status: str | None = None
    goal_handle: Any = field(default=None, repr=False)
    result_future: Any = field(default=None, repr=False)
    timeout_fault: bool = False
    cancellation_requested: bool = False
    retryable_terminal_failure: bool = False

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
        self._next_goal_timeout_fault_seconds: float | None = None

    def inject_timeout_on_next_goal(self) -> None:
        """Cause the next accepted goal to time out before its result is read."""
        self._next_goal_timeout_fault_seconds = _TIMEOUT_FAULT_SECONDS

    def _record_attempt(self, attempt: GoalAttemptRecord) -> None:
        """Retain each Nav2 UUID while indexing the latest attempt to reconcile."""
        self.goal_attempts.append(attempt)
        self._attempts_by_action_id[attempt.action_id] = attempt

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
        # SIM-004 launches into this private domain.  rclpy reads the setting
        # when its context is initialized, so share that exact domain here.
        previous_domain = os.environ.get("ROS_DOMAIN_ID")
        os.environ["ROS_DOMAIN_ID"] = self.environment["ROS_DOMAIN_ID"]
        try:
            rclpy.init(args=None)
        finally:
            if previous_domain is None:
                os.environ.pop("ROS_DOMAIN_ID", None)
            else:
                os.environ["ROS_DOMAIN_ID"] = previous_domain
        node = rclpy.create_node("sim009_goal_tracker")
        client = ActionClient(node, NavigateToPose, "/navigate_to_pose")
        self._rclpy, self._node, self._action_client = rclpy, node, client
        self._goal_type = (NavigateToPose, PoseStamped)
        return rclpy, node, client, self._goal_type

    @staticmethod
    def _uuid(goal_handle: Any) -> str:
        return str(uuid.UUID(bytes=bytes(goal_handle.goal_id.uuid)))

    def _observation_from_result(self, attempt: GoalAttemptRecord) -> RuntimeObservation:
        result = attempt.result_future.result()
        status = result.status
        attempt.terminal_status = str(status)
        # nav2_msgs/action status codes: SUCCEEDED=4.  The result future is
        # attached to the same ClientGoalHandle, not a second lookup goal.
        if status == 4:
            return RuntimeObservation("succeeded", arrival_verified=True)
        return RuntimeObservation(
            "failed", error_code="NAVIGATION_ABORTED",
            error_message=f"Nav2 terminal goal status {status}",
            retryable=attempt.retryable_terminal_failure,
        )

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
        client_parts = self._client()
        if client_parts is None:
            return RuntimeObservation("failed", error_code="NAV2_CLIENT_UNAVAILABLE", error_message="rclpy/Nav2 client is unavailable", error_category="RESOURCE_UNAVAILABLE")
        rclpy, node, client, (goal_type, pose_type) = client_parts
        timeout = max(0.001, min(30.0, request["timeout_ms"] / 1000))
        if not client.wait_for_server(timeout_sec=timeout):
            return RuntimeObservation("failed", error_code="NAV2_ACTION_UNAVAILABLE", error_message="NavigateToPose action server is unavailable", error_category="RESOURCE_UNAVAILABLE")
        x, y = _GOAL_POINTS[request["destination_id"]]
        goal = goal_type.Goal()
        goal.pose = pose_type()
        goal.pose.header.frame_id = "map"
        goal.pose.pose.position.x, goal.pose.pose.position.y = x, y
        goal.pose.pose.orientation.w = 1.0
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
        )
        self._record_attempt(attempt)
        execution_timeout = timeout_fault if timeout_fault is not None else timeout
        rclpy.spin_until_future_complete(node, attempt.result_future, timeout_sec=execution_timeout)
        if not attempt.result_future.done():
            return RuntimeObservation("unknown", error_code="NAVIGATION_TIMEOUT", error_message="same Nav2 goal exceeded its bounded execution window", error_category="DEPENDENCY_TIMEOUT", retryable=True)
        return self._observation_from_result(attempt)

    def reconcile(self, action_id: str) -> RuntimeObservation:
        attempt = self._attempts_by_action_id[action_id]
        if not attempt.result_future.done():
            if attempt.timeout_fault:
                return self._reconcile_timeout_attempt(attempt)
            self._rclpy.spin_until_future_complete(self._node, attempt.result_future, timeout_sec=5.0)
        if not attempt.result_future.done():
            return RuntimeObservation("unknown", error_code="NAVIGATION_RECONCILIATION_PENDING", error_message="same Nav2 goal has no terminal result", error_category="DEPENDENCY_TIMEOUT", retryable=False)
        return self._observation_from_result(attempt)

    def evidence(self) -> dict[str, Any]:
        return {
            "goal_attempts": [
                {"mission_id": item.mission_id, "action_id": item.action_id,
                 "idempotency_key": item.idempotency_key, "destination_id": item.destination_id,
                 "nav2_goal_uuid": item.nav2_goal_uuid, "terminal_goal_uuid": item.terminal_goal_uuid,
                 "terminal_status": item.terminal_status, "timeout_fault": item.timeout_fault,
                 "cancellation_requested": item.cancellation_requested,
                 "retryable_terminal_failure": item.retryable_terminal_failure}
                for item in self.goal_attempts
            ],
            "cleanup": self.measurements.get("cleanup", {}),
        }

    def close(self) -> bool:
        if self._node is not None:
            self._node.destroy_node()
            self._rclpy.shutdown()
            self._node = self._action_client = self._rclpy = None
        return super().close()
