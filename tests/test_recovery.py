from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from factory_tools import DeterministicTimeoutRecoverySkillFake, FactoryToolGateway
from mission_runtime import ActionStatus, MissionStatus
from mission_runtime.recovery import SingleFailureRecoveryCoordinator

MISSION_ID = "0d47cf1c-31c9-4f80-a8ac-6bd1a8726194"
FIRST_ACTION_ID = "4bca5507-7941-40e4-aac5-7d8a97111b08"
RETRY_ACTION_ID = "078ded37-76b9-4303-a4f7-042373ac4200"
REQUEST_IDS = (
    "35ae5d55-ca49-4962-ba84-2d0093e46f7f",
    "e48b780f-bd36-45ff-9d77-c350cc004d4f",
    "4a9de93e-f590-4b6b-9f60-fb24eb4464c6",
)
TIMESTAMP = "2026-08-28T00:00:00Z"
DEADLINE = "2026-08-28T00:05:00Z"
IDEMPOTENCY_KEY = "mission-0d47cf1c-transfer-1"


def run_fixture(*, reconciliation_retryable: bool = True):
    fixture = DeterministicTimeoutRecoverySkillFake(reconciliation_retryable=reconciliation_retryable)
    coordinator = SingleFailureRecoveryCoordinator(FactoryToolGateway(robot_skill=fixture))
    return coordinator.run(
        mission_id=MISSION_ID,
        idempotency_key=IDEMPOTENCY_KEY,
        first_action_id=FIRST_ACTION_ID,
        retry_action_id=RETRY_ACTION_ID,
        request_ids=REQUEST_IDS,
        timestamp=TIMESTAMP,
        deadline_at=DEADLINE,
    )


class SingleFailureRecoveryTests(unittest.TestCase):
    def test_timeout_reconciles_once_then_retry_succeeds(self) -> None:
        run = run_fixture()

        self.assertEqual(
            run.first_action_state_sequence,
            (
                ActionStatus.REQUESTED,
                ActionStatus.EXECUTING,
                ActionStatus.UNKNOWN,
                ActionStatus.RECONCILING,
                ActionStatus.FAILED,
            ),
        )
        self.assertEqual(
            run.mission_state_sequence,
            (
                MissionStatus.CREATED,
                MissionStatus.READY,
                MissionStatus.EXECUTING,
                MissionStatus.RECONCILING,
                MissionStatus.RECOVERING,
                MissionStatus.EXECUTING,
                MissionStatus.COMPLETED,
            ),
        )
        self.assertEqual(run.call_trace, ("transfer:timeout", "status:reconciled_failure", "transfer:success"))
        self.assertTrue(run.reconciliation_retryable)
        self.assertEqual(run.mission.retry_count, 1)
        self.assertEqual(run.mission.status, MissionStatus.COMPLETED)
        self.assertIsNotNone(run.retry_action)
        self.assertEqual(run.retry_action.status, ActionStatus.SUCCEEDED)  # type: ignore[union-attr]

    def test_non_retryable_reconciliation_escalates_without_retry(self) -> None:
        run = run_fixture(reconciliation_retryable=False)

        self.assertEqual(run.mission.status, MissionStatus.ESCALATED)
        self.assertEqual(run.mission.retry_count, 0)
        self.assertIsNone(run.retry_action)
        self.assertFalse(run.reconciliation_retryable)
        self.assertEqual(run.call_trace, ("transfer:timeout", "status:reconciled_failure"))

    def test_runtime_owns_retry_budget_and_agent_cannot_supply_outcome(self) -> None:
        fixture = DeterministicTimeoutRecoverySkillFake()
        with self.assertRaises(TypeError):
            SingleFailureRecoveryCoordinator(FactoryToolGateway(robot_skill=fixture), retry_budget=2)  # type: ignore[call-arg]
        coordinator = SingleFailureRecoveryCoordinator(FactoryToolGateway(robot_skill=fixture))
        with self.assertRaises(TypeError):
            coordinator.run(outcome="succeeded")  # type: ignore[call-arg]


if __name__ == "__main__":
    unittest.main()
