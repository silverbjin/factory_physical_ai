from __future__ import annotations

import json
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from factory_agent import DeterministicFakeProvider, FactoryAgent
from factory_tools import DeterministicTimeoutRecoverySkillFake, FactoryToolGateway
from mission_runtime import ActionStatus, MissionStatus
from mission_runtime.failure_recovery import (
    CanonicalFailureRecoveryE2EExecutor,
    FailureRecoveryMissionError,
    write_failure_recovery_e2e_latest,
)
from mission_runtime.normal import fixed_runtime_metadata
from mission_runtime.persistence import write_run_artifacts

CANONICAL_MISSION = "Line B에 Brake ECU Type-B 1개를 공급해줘."
INVENTORY_REQUEST_ID = "9fb6583f-7997-48fa-a41c-a10bd5714507"
RECOVERY_REQUEST_IDS = (
    "35ae5d55-ca49-4962-ba84-2d0093e46f7f",
    "e48b780f-bd36-45ff-9d77-c350cc004d4f",
    "4a9de93e-f590-4b6b-9f60-fb24eb4464c6",
)
FIRST_ACTION_ID = "4bca5507-7941-40e4-aac5-7d8a97111b08"
RETRY_ACTION_ID = "078ded37-76b9-4303-a4f7-042373ac4200"
TIMESTAMP = "2026-08-29T00:00:00Z"
COMPLETED_AT = "2026-08-29T00:00:05Z"
DEADLINE = "2026-08-29T00:05:00Z"
RUN_ID = "mvp-007-canonical-failure-recovery-20260829T000000Z"


def run_fixture():
    skill = DeterministicTimeoutRecoverySkillFake()
    agent = FactoryAgent(DeterministicFakeProvider(), runtime_metadata_factory=fixed_runtime_metadata)
    executor = CanonicalFailureRecoveryE2EExecutor(agent, FactoryToolGateway(robot_skill=skill))
    return (
        executor.run(
            CANONICAL_MISSION,
            inventory_request_id=INVENTORY_REQUEST_ID,
            recovery_request_ids=RECOVERY_REQUEST_IDS,
            first_action_id=FIRST_ACTION_ID,
            retry_action_id=RETRY_ACTION_ID,
            idempotency_key="mission-0d47cf1c-transfer-1",
            timestamp=TIMESTAMP,
            deadline_at=DEADLINE,
        ),
        skill,
    )


class CanonicalFailureRecoveryE2ETests(unittest.TestCase):
    def test_single_timeout_reconciles_before_one_retry_and_completes(self) -> None:
        run, skill = run_fixture()

        self.assertEqual(run.mission_request.part_id, "Brake ECU Type-B")
        self.assertEqual(run.mission_request.quantity, 1)
        self.assertEqual(run.mission_request.destination, "Line B")
        self.assertEqual(run.inventory.source_location, "Rack A19")
        self.assertEqual(skill.call_trace, ["transfer:timeout", "status:reconciled_failure", "transfer:success"])
        self.assertEqual(run.recovery.first_action.status, ActionStatus.FAILED)
        self.assertEqual(run.recovery.retry_action.status, ActionStatus.SUCCEEDED)  # type: ignore[union-attr]
        self.assertEqual(run.recovery.mission.status, MissionStatus.COMPLETED)
        self.assertEqual(run.recovery.mission.retry_count, 1)
        self.assertEqual(run.recovery.mission_state_sequence[3:5], (MissionStatus.RECONCILING, MissionStatus.RECOVERING))

    def test_failure_recovery_evidence_references_durable_sequence(self) -> None:
        run, _ = run_fixture()
        with tempfile.TemporaryDirectory() as temporary_directory:
            artifacts = write_run_artifacts(
                run.recovery,
                run_root=Path(temporary_directory) / RUN_ID,
                run_id=RUN_ID,
                started_at=TIMESTAMP,
                completed_at=COMPLETED_AT,
            )
            latest_path = write_failure_recovery_e2e_latest(
                run, artifacts, Path(temporary_directory) / "latest.json"
            )
            latest = json.loads(latest_path.read_text(encoding="utf-8"))
            trace = [json.loads(line) for line in artifacts.trace_path.read_text(encoding="utf-8").splitlines()]

        self.assertTrue(latest["timeout_detected"])
        self.assertTrue(latest["reconciliation_performed"])
        self.assertEqual(latest["retry_budget"], 1)
        self.assertEqual(latest["retry_count"], 1)
        self.assertEqual(latest["recovery_result"], ActionStatus.SUCCEEDED.value)
        self.assertEqual(latest["mission_result"], MissionStatus.COMPLETED.value)
        self.assertEqual(latest["inventory"]["source_location"], "Rack A19")
        self.assertEqual(latest["logical_transfer_count"], 2)
        self.assertEqual(latest["extra_execution_count"], 0)
        self.assertEqual([event["event_type"] for event in trace], [
            "timeout_detected", "reconciliation_performed", "recovery_completed"
        ])

    def test_e2e_evidence_rejects_tampered_inventory_correlation(self) -> None:
        run, _ = run_fixture()
        with tempfile.TemporaryDirectory() as temporary_directory:
            artifacts = write_run_artifacts(
                run.recovery,
                run_root=Path(temporary_directory) / RUN_ID,
                run_id=RUN_ID,
                started_at=TIMESTAMP,
                completed_at=COMPLETED_AT,
            )
            tampered = replace(
                run,
                inventory=replace(run.inventory, request_id="b5cb362a-edbd-4d4b-8b56-4d0976178d34"),
            )
            with self.assertRaises(FailureRecoveryMissionError):
                write_failure_recovery_e2e_latest(tampered, artifacts, Path(temporary_directory) / "latest.json")


if __name__ == "__main__":
    unittest.main()
