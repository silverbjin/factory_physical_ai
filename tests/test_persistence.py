from __future__ import annotations

import json
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from uuid import UUID

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from factory_tools import DeterministicTimeoutRecoverySkillFake, FactoryToolGateway
from mission_runtime import ActionStatus, MissionStatus
from mission_runtime.persistence import MissionLifecycleStore, PersistenceValidationError, write_run_artifacts
from mission_runtime.recovery import SingleFailureRecoveryCoordinator

MISSION_ID = "0d47cf1c-31c9-4f80-a8ac-6bd1a8726194"
FIRST_ACTION_ID = "4bca5507-7941-40e4-aac5-7d8a97111b08"
RETRY_ACTION_ID = "078ded37-76b9-4303-a4f7-042373ac4200"
REQUEST_IDS = (
    "35ae5d55-ca49-4962-ba84-2d0093e46f7f",
    "e48b780f-bd36-45ff-9d77-c350cc004d4f",
    "4a9de93e-f590-4b6b-9f60-fb24eb4464c6",
)
TIMESTAMP = "2026-08-29T00:00:00Z"
COMPLETED_AT = "2026-08-29T00:00:05Z"
DEADLINE = "2026-08-29T00:05:00Z"
RUN_ID = "mvp-005-canonical-recovery"


def canonical_recovery_run():
    coordinator = SingleFailureRecoveryCoordinator(
        FactoryToolGateway(robot_skill=DeterministicTimeoutRecoverySkillFake())
    )
    return coordinator.run(
        mission_id=MISSION_ID,
        idempotency_key="mission-0d47cf1c-transfer-1",
        first_action_id=FIRST_ACTION_ID,
        retry_action_id=RETRY_ACTION_ID,
        request_ids=REQUEST_IDS,
        timestamp=TIMESTAMP,
        deadline_at=DEADLINE,
    )


class PersistenceTests(unittest.TestCase):
    def write_artifacts(self, directory: Path):
        return write_run_artifacts(
            canonical_recovery_run(),
            run_root=directory / RUN_ID,
            run_id=RUN_ID,
            started_at=TIMESTAMP,
            completed_at=COMPLETED_AT,
        )

    def test_sqlite_schema_and_mission_action_lifecycle_are_persisted(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            artifacts = self.write_artifacts(Path(temporary_directory))
            self.assertTrue(artifacts.database_path.exists())
            store = MissionLifecycleStore(artifacts.database_path)
            try:
                summary = store.load_summary(RUN_ID)
                table_names = {
                    row["name"]
                    for row in store._connection.execute(
                        "SELECT name FROM sqlite_master WHERE type = 'table'"
                    )
                }
            finally:
                store.close()

        self.assertTrue(
            {"runs", "missions", "actions", "mission_transitions", "action_transitions", "attempted_calls", "events"}
            <= table_names
        )
        self.assertEqual(summary["mission_id"], MISSION_ID)
        self.assertEqual(summary["mission_result"], MissionStatus.COMPLETED.value)
        self.assertEqual(summary["action_ids"], [FIRST_ACTION_ID, RETRY_ACTION_ID])
        self.assertEqual(summary["retry_count"], 1)
        self.assertEqual([call["request_id"] for call in summary["attempted_calls"]], list(REQUEST_IDS))  # type: ignore[index]
        self.assertEqual(summary["state_transitions"]["mission"][3], MissionStatus.RECONCILING.value)  # type: ignore[index]

    def test_unknown_transition_remains_unknown_after_database_reload(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            artifacts = self.write_artifacts(Path(temporary_directory))
            reloaded_store = MissionLifecycleStore(artifacts.database_path)
            try:
                unknown_state = reloaded_store.load_action_state(RUN_ID, FIRST_ACTION_ID, ordinal=2)
            finally:
                reloaded_store.close()

        self.assertEqual(unknown_state.status, ActionStatus.UNKNOWN)
        self.assertEqual(unknown_state.mission_id, MISSION_ID)
        self.assertEqual(unknown_state.action_id, FIRST_ACTION_ID)
        self.assertFalse(unknown_state.retryable)

    def test_jsonl_trace_is_parseable_and_evidence_reconstructs_run(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            artifacts = self.write_artifacts(Path(temporary_directory))
            trace = [json.loads(line) for line in artifacts.trace_path.read_text(encoding="utf-8").splitlines()]
            summary = json.loads(artifacts.summary_path.read_text(encoding="utf-8"))

        self.assertEqual([event["event_type"] for event in trace], [
            "timeout_detected",
            "reconciliation_performed",
            "recovery_completed",
        ])
        self.assertTrue(summary["timeout_detected"])
        self.assertTrue(summary["reconciliation_performed"])
        self.assertEqual(summary["recovery_result"], ActionStatus.SUCCEEDED.value)
        self.assertEqual(summary["mission_duration_ms"], 5000)
        for event, request_id in zip(trace, REQUEST_IDS, strict=True):
            self.assertEqual(event["request_id"], request_id)
            self.assertEqual(event["component_version"], "mvp-003")
            self.assertEqual(event["mission_id"], MISSION_ID)
            UUID(event["action_id"])

    def test_evidence_references_valid_mission_and_action_ids(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            summary = self.write_artifacts(Path(temporary_directory)).summary

        UUID(summary["mission_id"])  # type: ignore[arg-type]
        for action_id in summary["action_ids"]:  # type: ignore[union-attr]
            UUID(action_id)
        for request_id in [call["request_id"] for call in summary["attempted_calls"]]:  # type: ignore[index]
            UUID(request_id)
        self.assertTrue(summary["tool_call_valid"])
        self.assertFalse(summary["hitl_escalated"])
        self.assertEqual(summary["error_category"], "DEPENDENCY_TIMEOUT")

    def test_tool_call_validity_is_derived_from_a_strict_attempted_call_trace(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            run = canonical_recovery_run()
            invalid_call = replace(run.attempted_calls[0], request_id="not-a-uuid")
            invalid_run = replace(run, attempted_calls=(invalid_call, *run.attempted_calls[1:]))

            with self.assertRaises(PersistenceValidationError):
                write_run_artifacts(
                    invalid_run,
                    run_root=Path(temporary_directory) / RUN_ID,
                    run_id=RUN_ID,
                    started_at=TIMESTAMP,
                    completed_at=COMPLETED_AT,
                )


if __name__ == "__main__":
    unittest.main()
