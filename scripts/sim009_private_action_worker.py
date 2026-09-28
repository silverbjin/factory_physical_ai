#!/usr/bin/env python3
"""Bounded ROS-Python action-client worker for SIM-009.

The qualification controller runs in a MuJoCo-focused venv.  ROS Jazzy's
``rclpy`` extension must instead be loaded by a process started with the
immutable ROS runtime environment, including its loader paths.
"""
from __future__ import annotations

import json
import sys
import uuid
from typing import Any


def _emit(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, sort_keys=True), flush=True)


def main() -> int:
    import rclpy
    from rclpy.action import ActionClient
    from rclpy.executors import SingleThreadedExecutor
    from nav2_msgs.action import NavigateToPose

    context: Any = None
    node: Any = None
    client: Any = None
    executor: Any = None
    pending: dict[str, tuple[Any, Any]] = {}

    def terminal_payload(goal_uuid: str, result_future: Any) -> dict[str, Any]:
        result = result_future.result()
        native = getattr(result, "result", None)
        return {
            "state": "terminal",
            "goal_uuid": goal_uuid,
            "terminal_status": int(result.status),
            "native_error_code": str(getattr(native, "error_code", "")) or None,
            "native_error_message": str(getattr(native, "error_msg", "")) or None,
        }
    try:
        for raw in sys.stdin:
            try:
                request = json.loads(raw)
                operation = request["operation"]
                if operation == "ready":
                    if context is None:
                        context = rclpy.context.Context()
                        rclpy.init(
                            args=None, context=context,
                            domain_id=int(request["domain_id"]),
                        )
                        node = rclpy.create_node(
                            "sim009_goal_tracker", context=context,
                        )
                        executor = SingleThreadedExecutor(context=context)
                        executor.add_node(node)
                        client = ActionClient(node, NavigateToPose, "/navigate_to_pose")
                    _emit({"ready": bool(client.wait_for_server(timeout_sec=5.0))})
                elif operation == "close":
                    _emit({"closed": True})
                    break
                elif operation == "execute":
                    if client is None or not client.wait_for_server(timeout_sec=5.0):
                        _emit({"state": "unavailable"})
                        continue
                    goal = NavigateToPose.Goal()
                    goal.pose.header.frame_id = str(request["frame_id"])
                    goal.pose.pose.position.x = float(request["x"])
                    goal.pose.pose.position.y = float(request["y"])
                    goal.pose.pose.orientation.w = 1.0
                    behavior_tree = str(request.get("behavior_tree", ""))
                    if behavior_tree:
                        goal.behavior_tree = behavior_tree
                    sent = client.send_goal_async(goal)
                    executor.spin_until_future_complete(
                        sent, timeout_sec=float(request["timeout_seconds"]),
                    )
                    if not sent.done() or not sent.result().accepted:
                        _emit({"state": "rejected"})
                        continue
                    handle = sent.result()
                    goal_uuid = str(uuid.UUID(bytes=bytes(handle.goal_id.uuid)))
                    result_future = handle.get_result_async()
                    wait = 0.001 if request.get("timeout_fault") else float(request["timeout_seconds"])
                    executor.spin_until_future_complete(result_future, timeout_sec=wait)
                    if result_future.done():
                        _emit(terminal_payload(goal_uuid, result_future))
                    else:
                        pending[str(request["action_id"])] = (handle, result_future)
                        _emit({"state": "pending", "goal_uuid": goal_uuid})
                elif operation == "reconcile":
                    action_id = str(request["action_id"])
                    saved = pending.pop(action_id, None)
                    if saved is None:
                        _emit({"state": "missing"})
                        continue
                    handle, result_future = saved
                    cancellation = handle.cancel_goal_async()
                    executor.spin_until_future_complete(cancellation, timeout_sec=2.0)
                    if not cancellation.done():
                        _emit({"state": "pending"})
                        continue
                    executor.spin_until_future_complete(result_future, timeout_sec=2.0)
                    if not result_future.done():
                        _emit({"state": "pending"})
                        continue
                    _emit(terminal_payload(
                        str(uuid.UUID(bytes=bytes(handle.goal_id.uuid))), result_future,
                    ))
                else:
                    _emit({"error": f"UNSUPPORTED_OPERATION:{operation}"})
            except Exception as exc:
                _emit({"error": f"{type(exc).__name__}: {exc}"})
    finally:
        if executor is not None:
            executor.remove_node(node)
            executor.shutdown()
        if node is not None:
            node.destroy_node()
        if context is not None:
            rclpy.shutdown(context=context)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
