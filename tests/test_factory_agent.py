from __future__ import annotations

import sys
import unittest
from pathlib import Path
from uuid import UUID

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from contracts import MissionProposal, MissionRequest, MissionValidationError
from factory_agent import DeterministicFakeProvider, FactoryAgent, UnsupportedMissionError
from factory_agent.service import CANONICAL_MISSION

VALID_PROPOSAL = {
    "mission_type": "line_side_parts_transfer",
    "part_id": "Brake ECU Type-B",
    "quantity": 1,
    "destination": "Line B",
}
VALID_REQUEST = {
    "schema_version": "v1",
    "request_id": "35ae5d55-ca49-4962-ba84-2d0093e46f7f",
    "mission_id": "0d47cf1c-31c9-4f80-a8ac-6bd1a8726194",
    **VALID_PROPOSAL,
    "requested_by": "operator",
    "created_at": "2026-08-28T00:00:00Z",
}


class StaticProvider:
    def __init__(self, output: object) -> None:
        self._output = output

    def propose_mission(self, natural_language_mission: str) -> object:
        return self._output


def fixed_runtime_metadata() -> dict[str, object]:
    return {
        "request_id": VALID_REQUEST["request_id"],
        "mission_id": VALID_REQUEST["mission_id"],
        "requested_by": VALID_REQUEST["requested_by"],
        "created_at": VALID_REQUEST["created_at"],
    }


class FactoryAgentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.provider = DeterministicFakeProvider()
        self.agent = FactoryAgent(self.provider, fixed_runtime_metadata)

    def test_canonical_korean_mission_parses_to_expected_business_fields(self) -> None:
        mission = self.agent.parse_mission(CANONICAL_MISSION)

        self.assertEqual(mission.part_id, "Brake ECU Type-B")
        self.assertEqual(mission.quantity, 1)
        self.assertEqual(mission.destination, "Line B")

    def test_service_owns_valid_runtime_metadata(self) -> None:
        mission = self.agent.parse_mission(CANONICAL_MISSION)

        self.assertEqual(mission.request_id, VALID_REQUEST["request_id"])
        self.assertEqual(mission.mission_id, VALID_REQUEST["mission_id"])
        self.assertEqual(mission.requested_by, "operator")
        self.assertEqual(mission.created_at, "2026-08-28T00:00:00Z")
        UUID(mission.request_id)
        UUID(mission.mission_id)

    def test_structured_mission_contains_all_required_fields(self) -> None:
        mission = self.agent.parse_mission(CANONICAL_MISSION)

        self.assertEqual(set(mission.to_dict()), set(VALID_REQUEST))

    def test_fake_provider_is_reproducible_at_semantic_proposal_level(self) -> None:
        proposal = self.provider.propose_mission(CANONICAL_MISSION)

        self.assertEqual(proposal, self.provider.propose_mission(CANONICAL_MISSION))
        self.assertEqual(proposal, VALID_PROPOSAL)

    def test_non_mapping_provider_outputs_fail_closed(self) -> None:
        for output in (None, [], (), "not a mapping", 1):
            with self.subTest(output=output):
                with self.assertRaises(MissionValidationError):
                    FactoryAgent(StaticProvider(output), fixed_runtime_metadata).parse_mission(CANONICAL_MISSION)

    def test_invalid_mapping_key_fails_closed(self) -> None:
        invalid_key_proposal = {**VALID_PROPOSAL, 1: "invalid"}

        with self.assertRaises(MissionValidationError):
            MissionProposal.from_mapping(invalid_key_proposal)

    def test_missing_required_provider_field_fails_closed(self) -> None:
        missing_destination = dict(VALID_PROPOSAL)
        del missing_destination["destination"]

        with self.assertRaises(MissionValidationError):
            MissionProposal.from_mapping(missing_destination)

    def test_complete_provider_payload_with_extra_field_fails_closed(self) -> None:
        extra_field_proposal = {**VALID_PROPOSAL, "execution_command": "not allowed"}

        with self.assertRaises(MissionValidationError):
            MissionProposal.from_mapping(extra_field_proposal)

    def test_invalid_quantities_fail_closed(self) -> None:
        for quantity in (0, -1, True, False, 1.0, "1"):
            with self.subTest(quantity=quantity):
                with self.assertRaises(MissionValidationError):
                    MissionProposal.from_mapping({**VALID_PROPOSAL, "quantity": quantity})

    def test_whitespace_only_provider_strings_fail_closed(self) -> None:
        for field_name in ("part_id", "destination"):
            with self.subTest(field_name=field_name):
                with self.assertRaises(MissionValidationError):
                    MissionProposal.from_mapping({**VALID_PROPOSAL, field_name: "   "})

    def test_whitespace_only_requested_by_fails_closed(self) -> None:
        with self.assertRaises(MissionValidationError):
            MissionRequest.from_mapping({**VALID_REQUEST, "requested_by": "   "})

    def test_naive_timestamp_fails_closed(self) -> None:
        with self.assertRaises(MissionValidationError):
            MissionRequest.from_mapping({**VALID_REQUEST, "created_at": "2026-08-28T00:00:00"})

    def test_valid_utc_timestamp_and_uuids_are_accepted(self) -> None:
        mission = MissionRequest.from_mapping({**VALID_REQUEST, "created_at": "2026-08-28T00:00:00+00:00"})

        self.assertEqual(mission.created_at, "2026-08-28T00:00:00+00:00")
        UUID(mission.request_id)
        UUID(mission.mission_id)

    def test_invalid_request_and_mission_ids_fail_closed(self) -> None:
        for field_name in ("request_id", "mission_id"):
            with self.subTest(field_name=field_name):
                with self.assertRaises(MissionValidationError):
                    MissionRequest.from_mapping({**VALID_REQUEST, field_name: "not-a-uuid"})

    def test_no_execution_layer_command_is_generated(self) -> None:
        mission = self.agent.parse_mission(CANONICAL_MISSION)

        self.assertNotIn("execution_command", mission.to_dict())
        self.assertFalse(hasattr(mission, "execution_command"))

    def test_noncanonical_request_is_not_interpreted(self) -> None:
        with self.assertRaises(UnsupportedMissionError):
            self.agent.parse_mission("Move the robot to Line B.")


if __name__ == "__main__":
    unittest.main()
