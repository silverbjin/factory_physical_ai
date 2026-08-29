from __future__ import annotations

import json
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from factory_agent import DeterministicFakeProvider, FactoryAgent
from factory_tools import DeterministicRobotSkillFake, FactoryToolGateway, ToolResultKind
from mission_runtime import ActionStatus, MissionStatus
from mission_runtime.normal import CanonicalNormalMissionExecutor, fixed_runtime_metadata
from mission_runtime.persistence import (
    MissionLifecycleStore,
    PersistenceValidationError,
    write_normal_e2e_latest,
    write_normal_run_artifacts,
)

CANONICAL_MISSION = "Line B에 Brake ECU Type-B 1개를 공급해줘."
INVENTORY_REQUEST_ID = "9fb6583f-7997-48fa-a41c-a10bd5714507"
TRANSFER_REQUEST_ID = "e0354a9f-743f-4e01-a18c-4c0a03e4f5d4"
ACTION_ID = "33ce8e48-98dd-4cc2-9618-59cf77f17eb9"
TIMESTAMP = "2026-08-29T00:00:00Z"
COMPLETED_AT = "2026-08-29T00:00:05Z"
DEADLINE = "2026-08-29T00:05:00Z"
RUN_ID = "mvp-006-canonical-normal-20260829T000000Z"


class CountingSuccessfulRobotSkillFake(DeterministicRobotSkillFake):
    """Test-only counter proving the normal executor dispatches one logical transfer."""

    def __init__(self) -> None:
        super().__init__()
        self.transfer_calls = 0

    def transfer_part(self, request):  # type: ignore[no-untyped-def]
        self.transfer_calls += 1
        return super().transfer_part(request)


def run_fixture() -> tuple[object, CountingSuccessfulRobotSkillFake]:
    robot_skill = CountingSuccessfulRobotSkillFake()
    agent = FactoryAgent(DeterministicFakeProvider(), runtime_metadata_factory=fixed_runtime_metadata)
    executor = CanonicalNormalMissionExecutor(agent, FactoryToolGateway(robot_skill=robot_skill))
    return (
        executor.run(
            CANONICAL_MISSION,
            inventory_request_id=INVENTORY_REQUEST_ID,
            transfer_request_id=TRANSFER_REQUEST_ID,
            action_id=ACTION_ID,
            idempotency_key="mission-0d47cf1c-transfer-1",
            timestamp=TIMESTAMP,
            deadline_at=DEADLINE,
        ),
        robot_skill,
    )


class CanonicalNormalE2ETests(unittest.TestCase):
    def test_canonical_text_reaches_completed_through_agent_wms_and_one_transfer(self) -> None:
        run, robot_skill = run_fixture()

        self.assertEqual(run.mission_request.part_id, "Brake ECU Type-B")
        self.assertEqual(run.mission_request.quantity, 1)
        self.assertEqual(run.mission_request.destination, "Line B")
        self.assertEqual(run.inventory.source_location, "Rack A19")
        self.assertEqual(robot_skill.transfer_calls, 1)
        self.assertEqual(run.transfer.status, ActionStatus.SUCCEEDED)
        self.assertEqual(run.mission.status, MissionStatus.COMPLETED)
        self.assertEqual(run.mission.retry_count, 0)
        self.assertEqual(
            run.mission_state_sequence,
            (MissionStatus.CREATED, MissionStatus.READY, MissionStatus.EXECUTING, MissionStatus.COMPLETED),
        )

    def test_normal_run_evidence_is_machine_readable_and_reconstructable(self) -> None:
        run, _ = run_fixture()
        with tempfile.TemporaryDirectory() as temporary_directory:
            run_root = Path(temporary_directory) / RUN_ID
            artifacts = write_normal_run_artifacts(
                run,
                run_root=run_root,
                run_id=RUN_ID,
                started_at=TIMESTAMP,
                completed_at=COMPLETED_AT,
            )
            latest_path = write_normal_e2e_latest(artifacts, Path(temporary_directory) / "latest.json")
            latest = artifacts.summary
            trace = [json.loads(line) for line in artifacts.trace_path.read_text(encoding="utf-8").splitlines()]
            latest_document = json.loads(latest_path.read_text(encoding="utf-8"))
            reloaded_store = MissionLifecycleStore(artifacts.database_path)
            try:
                reloaded = reloaded_store.load_summary(RUN_ID)
            finally:
                reloaded_store.close()

        self.assertEqual(latest["mission_result"], MissionStatus.COMPLETED.value)
        self.assertFalse(latest["timeout_detected"])
        self.assertFalse(latest["reconciliation_performed"])
        self.assertEqual(latest["retry_count"], 0)
        self.assertEqual(latest["source_location"], "Rack A19")
        self.assertEqual(latest["action_ids"], [ACTION_ID])
        self.assertEqual(latest_document["run_id"], RUN_ID)
        self.assertEqual(latest_document["artifact_paths"]["summary_json"], str(artifacts.summary_path))
        self.assertEqual([event["event_type"] for event in trace], ["inventory_resolved", "transfer_succeeded"])
        self.assertEqual([event["request_id"] for event in trace], [INVENTORY_REQUEST_ID, TRANSFER_REQUEST_ID])
        self.assertEqual(reloaded["mission_result"], MissionStatus.COMPLETED.value)
        self.assertEqual(reloaded["action_ids"], [ACTION_ID])
        self.assertEqual(reloaded["retry_count"], 0)
        self.assertFalse(reloaded["timeout_detected"])

    def test_persistence_rejects_tampered_normal_run_correlation_or_tool_result(self) -> None:
        run, _ = run_fixture()
        invalid_runs = (
            replace(
                run,
                attempted_calls=(
                    replace(run.attempted_calls[0], request_id="b5cb362a-edbd-4d4b-8b56-4d0976178d34"),
                    run.attempted_calls[1],
                ),
            ),
            replace(
                run,
                attempted_calls=(
                    run.attempted_calls[0],
                    replace(run.attempted_calls[1], request_id="b5cb362a-edbd-4d4b-8b56-4d0976178d34"),
                ),
            ),
            replace(run, inventory=replace(run.inventory, result=ToolResultKind.FAILURE)),
            replace(run, transfer=replace(run.transfer, result=ToolResultKind.FAILURE)),
        )
        with tempfile.TemporaryDirectory() as temporary_directory:
            for ordinal, invalid_run in enumerate(invalid_runs):
                with self.subTest(ordinal=ordinal):
                    with self.assertRaises(PersistenceValidationError):
                        write_normal_run_artifacts(
                            invalid_run,
                            run_root=Path(temporary_directory) / f"invalid-{ordinal}",
                            run_id=f"invalid-{ordinal}",
                            started_at=TIMESTAMP,
                            completed_at=COMPLETED_AT,
                        )


if __name__ == "__main__":
    unittest.main()
