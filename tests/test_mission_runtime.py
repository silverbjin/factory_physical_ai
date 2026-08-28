from __future__ import annotations

import sys
import unittest
from dataclasses import FrozenInstanceError
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from mission_runtime import ActionRecord, ActionStatus, MissionRecord, MissionStatus, StateTransitionError

MISSION_ID = "0d47cf1c-31c9-4f80-a8ac-6bd1a8726194"
ACTION_ID = "35ae5d55-ca49-4962-ba84-2d0093e46f7f"
TIMESTAMP = "2026-08-28T00:00:00Z"
DEADLINE = "2026-08-28T00:05:00Z"


def action_record() -> ActionRecord:
    return ActionRecord(
        mission_id=MISSION_ID,
        action_id=ACTION_ID,
        idempotency_key="mission-0d47cf1c-action-1",
        schema_version="v1",
        timestamp=TIMESTAMP,
        deadline=DEADLINE,
        component_version="mvp-002",
    )


def executing_mission() -> MissionRecord:
    return MissionRecord(MISSION_ID).transition(MissionStatus.READY).transition(MissionStatus.EXECUTING)


class MissionRuntimeTests(unittest.TestCase):
    def test_created_transitions_to_ready(self) -> None:
        mission = MissionRecord(MISSION_ID).transition(MissionStatus.READY)

        self.assertEqual(mission.status, MissionStatus.READY)

    def test_ready_transitions_to_executing(self) -> None:
        mission = MissionRecord(MISSION_ID).transition(MissionStatus.READY).transition(MissionStatus.EXECUTING)

        self.assertEqual(mission.status, MissionStatus.EXECUTING)

    def test_successful_action_completes_executing_mission(self) -> None:
        action = action_record().transition(ActionStatus.EXECUTING, timestamp=TIMESTAMP).transition(
            ActionStatus.SUCCEEDED, timestamp=TIMESTAMP
        )

        mission = executing_mission().apply_action_observation(action)

        self.assertEqual(mission.status, MissionStatus.COMPLETED)

    def test_ambiguous_action_moves_mission_to_reconciling(self) -> None:
        action = action_record().transition(ActionStatus.EXECUTING, timestamp=TIMESTAMP).transition(
            ActionStatus.UNKNOWN, error="ambiguous_action_result", timestamp=TIMESTAMP
        )

        mission = executing_mission().apply_action_observation(action)

        self.assertEqual(mission.status, MissionStatus.RECONCILING)

    def test_retryable_reconciled_failure_moves_mission_to_recovering(self) -> None:
        action = (
            action_record()
            .transition(ActionStatus.EXECUTING, timestamp=TIMESTAMP)
            .transition(ActionStatus.UNKNOWN, error="ambiguous_action_result", timestamp=TIMESTAMP)
            .transition(ActionStatus.RECONCILING, timestamp=TIMESTAMP)
            .transition(ActionStatus.FAILED, error="action_not_found", retryable=True, timestamp=TIMESTAMP)
        )
        reconciling_mission = executing_mission().transition(MissionStatus.RECONCILING)

        mission = reconciling_mission.apply_action_observation(action)

        self.assertEqual(mission.status, MissionStatus.RECOVERING)

    def test_recovering_uses_only_one_bounded_retry(self) -> None:
        mission = MissionRecord(MISSION_ID, status=MissionStatus.RECOVERING).transition(MissionStatus.EXECUTING)

        self.assertEqual(mission.status, MissionStatus.EXECUTING)
        self.assertEqual(mission.retry_count, 1)
        with self.assertRaises(StateTransitionError):
            MissionRecord(MISSION_ID, status=MissionStatus.RECOVERING, retry_count=1).transition(
                MissionStatus.EXECUTING
            )

    def test_non_retryable_reconciled_failure_escalates(self) -> None:
        action = (
            action_record()
            .transition(ActionStatus.EXECUTING, timestamp=TIMESTAMP)
            .transition(ActionStatus.UNKNOWN, error="ambiguous_action_result", timestamp=TIMESTAMP)
            .transition(ActionStatus.RECONCILING, timestamp=TIMESTAMP)
            .transition(ActionStatus.FAILED, error="dependency_failed", retryable=False, timestamp=TIMESTAMP)
        )
        reconciling_mission = executing_mission().transition(MissionStatus.RECONCILING)

        mission = reconciling_mission.apply_action_observation(action)

        self.assertEqual(mission.status, MissionStatus.ESCALATED)

    def test_invalid_mission_and_action_transitions_fail_closed(self) -> None:
        with self.assertRaises(StateTransitionError):
            MissionRecord(MISSION_ID).transition(MissionStatus.EXECUTING)
        with self.assertRaises(StateTransitionError):
            action_record().transition(ActionStatus.SUCCEEDED)

    def test_unknown_is_not_success_and_cannot_transition_to_success(self) -> None:
        unknown_action = action_record().transition(ActionStatus.EXECUTING, timestamp=TIMESTAMP).transition(
            ActionStatus.UNKNOWN, error="ambiguous_action_result", timestamp=TIMESTAMP
        )

        self.assertNotEqual(unknown_action.status, ActionStatus.SUCCEEDED)
        with self.assertRaises(StateTransitionError):
            unknown_action.transition(ActionStatus.SUCCEEDED)

    def test_action_record_has_required_lifecycle_fields_and_is_immutable(self) -> None:
        action = action_record()

        self.assertEqual(
            {name for name in action.__dataclass_fields__ if not name.startswith("_")},
            {
                "mission_id",
                "action_id",
                "idempotency_key",
                "schema_version",
                "timestamp",
                "deadline",
                "status",
                "error",
                "retryable",
                "component_version",
            },
        )
        with self.assertRaises(FrozenInstanceError):
            action.status = ActionStatus.SUCCEEDED  # type: ignore[misc]


if __name__ == "__main__":
    unittest.main()
