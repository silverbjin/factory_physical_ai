from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from factory_tools import (
    DeterministicRobotSkillFake,
    FactoryToolGateway,
    ToolErrorCategory,
    ToolResultKind,
    ToolValidationError,
)
from mission_runtime import ActionStatus

MISSION_ID = "0d47cf1c-31c9-4f80-a8ac-6bd1a8726194"
REQUEST_ID = "35ae5d55-ca49-4962-ba84-2d0093e46f7f"
ACTION_ID = "4bca5507-7941-40e4-aac5-7d8a97111b08"
TIMESTAMP = "2026-08-28T00:00:00Z"
DEADLINE = "2026-08-28T00:05:00Z"


def inventory_query(**overrides: object) -> dict[str, object]:
    return {
        "schema_version": "v1",
        "mission_id": MISSION_ID,
        "request_id": REQUEST_ID,
        "part_id": "Brake ECU Type-B",
        "timestamp": TIMESTAMP,
        **overrides,
    }


def transfer_request(**overrides: object) -> dict[str, object]:
    return {
        "schema_version": "v1",
        "mission_id": MISSION_ID,
        "request_id": REQUEST_ID,
        "action_id": ACTION_ID,
        "idempotency_key": "mission-0d47cf1c-transfer-1",
        "part_id": "Brake ECU Type-B",
        "quantity": 1,
        "source_location": "Rack A19",
        "destination": "Line B",
        "timestamp": TIMESTAMP,
        "deadline_at": DEADLINE,
        "timeout_ms": 300_000,
        **overrides,
    }


def action_status_query(**overrides: object) -> dict[str, object]:
    return {
        "schema_version": "v1",
        "mission_id": MISSION_ID,
        "request_id": REQUEST_ID,
        "action_id": ACTION_ID,
        "timestamp": TIMESTAMP,
        **overrides,
    }


class FactoryToolGatewayTests(unittest.TestCase):
    def setUp(self) -> None:
        self.gateway = FactoryToolGateway()

    def test_canonical_inventory_lookup_returns_rack_a19(self) -> None:
        result = self.gateway.query_inventory(inventory_query())

        self.assertEqual(result.result, ToolResultKind.SUCCESS)
        self.assertEqual(result.source_location, "Rack A19")
        self.assertGreaterEqual(result.available_quantity, 1)
        self.assertEqual(result.source_kind, "mock")
        self.assertEqual(result.mission_id, MISSION_ID)
        self.assertEqual(result.request_id, REQUEST_ID)
        self.assertEqual(result.timestamp, TIMESTAMP)

    def test_unavailable_sku_returns_typed_failure(self) -> None:
        result = self.gateway.query_inventory(inventory_query(part_id="Unknown ECU"))

        self.assertEqual(result.result, ToolResultKind.FAILURE)
        self.assertEqual(result.available_quantity, 0)
        self.assertIsNotNone(result.error)
        self.assertEqual(result.error.category, ToolErrorCategory.RESOURCE_UNAVAILABLE)  # type: ignore[union-attr]

    def test_transfer_success_returns_typed_result_and_queryable_action_status(self) -> None:
        transfer = self.gateway.transfer_part(transfer_request())
        status = self.gateway.get_action_status(action_status_query())

        self.assertEqual(transfer.result, ToolResultKind.SUCCESS)
        self.assertEqual(transfer.status, ActionStatus.SUCCEEDED)
        self.assertEqual(transfer.mission_id, MISSION_ID)
        self.assertEqual(transfer.request_id, REQUEST_ID)
        self.assertEqual(transfer.idempotency_key, "mission-0d47cf1c-transfer-1")
        self.assertEqual(status.result, ToolResultKind.SUCCESS)
        self.assertEqual(status.status, ActionStatus.SUCCEEDED)
        self.assertEqual(status.source_kind, "mock")
        self.assertEqual(status.mission_id, MISSION_ID)
        self.assertEqual(status.request_id, REQUEST_ID)
        self.assertEqual(status.schema_version, "v1")
        self.assertEqual(status.timestamp, TIMESTAMP)

    def test_same_fixture_inputs_produce_same_results(self) -> None:
        first_gateway = FactoryToolGateway()
        second_gateway = FactoryToolGateway()

        self.assertEqual(first_gateway.query_inventory(inventory_query()), second_gateway.query_inventory(inventory_query()))
        self.assertEqual(first_gateway.transfer_part(transfer_request()), second_gateway.transfer_part(transfer_request()))

    def test_configured_failure_fixture_is_deterministic_and_queryable(self) -> None:
        gateway = FactoryToolGateway(robot_skill=DeterministicRobotSkillFake(ActionStatus.FAILED))

        transfer = gateway.transfer_part(transfer_request())
        status = gateway.get_action_status(action_status_query())

        self.assertEqual(transfer.result, ToolResultKind.FAILURE)
        self.assertEqual(transfer.status, ActionStatus.FAILED)
        self.assertEqual(status.status, ActionStatus.FAILED)
        self.assertFalse(transfer.error.retryable)  # type: ignore[union-attr]

    def test_malformed_requests_fail_closed(self) -> None:
        malformed_cases = (
            ("non_mapping", None),
            ("extra_field", {**inventory_query(), "raw_ros_command": "forbidden"}),
            ("blank_part", inventory_query(part_id="   ")),
            ("invalid_quantity", transfer_request(quantity=True)),
            ("naive_timestamp", transfer_request(timestamp="2026-08-28T00:00:00")),
            ("invalid_action_id", transfer_request(action_id="not-a-uuid")),
        )
        for name, request in malformed_cases:
            with self.subTest(name=name):
                if name in {"invalid_quantity", "naive_timestamp", "invalid_action_id"}:
                    with self.assertRaises(ToolValidationError):
                        self.gateway.transfer_part(request)
                else:
                    with self.assertRaises(ToolValidationError):
                        self.gateway.query_inventory(request)

    def test_unknown_or_malformed_action_status_query_fails_typed(self) -> None:
        unknown = self.gateway.get_action_status(action_status_query(action_id="4bca5507-7941-40e4-aac5-7d8a97111b09"))

        self.assertEqual(unknown.result, ToolResultKind.FAILURE)
        self.assertEqual(unknown.error.category, ToolErrorCategory.RESOURCE_UNAVAILABLE)  # type: ignore[union-attr]
        self.assertEqual(unknown.schema_version, "v1")
        self.assertEqual(unknown.mission_id, MISSION_ID)
        self.assertEqual(unknown.request_id, REQUEST_ID)
        self.assertEqual(unknown.timestamp, TIMESTAMP)
        for malformed in (
            None,
            {"action_id": ACTION_ID},
            action_status_query(action_id="not-a-uuid"),
            action_status_query(timestamp="2026-08-28T00:00:00"),
        ):
            with self.subTest(malformed=malformed):
                with self.assertRaises(ToolValidationError):
                    self.gateway.get_action_status(malformed)

    def test_no_raw_execution_layer_access_is_exposed(self) -> None:
        self.assertFalse(hasattr(self.gateway, "ros_command"))
        self.assertFalse(hasattr(self.gateway, "nav2"))
        self.assertFalse(hasattr(self.gateway, "moveit"))
        self.assertFalse(hasattr(self.gateway, "trajectory"))


if __name__ == "__main__":
    unittest.main()
