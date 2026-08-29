"""Deterministic canonical normal-path orchestration for TASK-MVP-006."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from contracts import MissionRequest
from factory_agent import FactoryAgent
from factory_tools import FactoryToolGateway, InventoryResult, ToolResultKind, TransferResult

from .recovery import AttemptedToolCall
from .state import ActionRecord, ActionStatus, MissionRecord, MissionStatus, StateTransitionError


class NormalMissionError(ValueError):
    """Raised when the single authorized normal MVP mission cannot complete safely."""


@dataclass(frozen=True, slots=True)
class NormalRun:
    """Immutable result of one normal canonical mission, prior to persistence."""

    operator_text: str
    mission_request: MissionRequest
    mission: MissionRecord
    action: ActionRecord
    inventory: InventoryResult
    transfer: TransferResult
    mission_state_sequence: tuple[MissionStatus, ...]
    action_state_sequence: tuple[ActionStatus, ...]
    attempted_calls: tuple[AttemptedToolCall, ...]


class CanonicalNormalMissionExecutor:
    """Runs the one Day-10 normal path through existing typed component boundaries."""

    def __init__(self, agent: FactoryAgent, gateway: FactoryToolGateway) -> None:
        self._agent = agent
        self._gateway = gateway

    def run(
        self,
        operator_text: str,
        *,
        inventory_request_id: str,
        transfer_request_id: str,
        action_id: str,
        idempotency_key: str,
        timestamp: str,
        deadline_at: str,
    ) -> NormalRun:
        """Execute exactly one successful fake transfer with no timeout/recovery branch."""
        mission_request = self._agent.parse_mission(operator_text)
        mission = MissionRecord(mission_request.mission_id)
        mission_states = [mission.status]
        mission = mission.transition(MissionStatus.READY)
        mission_states.append(mission.status)
        mission = mission.transition(MissionStatus.EXECUTING)
        mission_states.append(mission.status)

        action = ActionRecord(
            mission_id=mission_request.mission_id,
            action_id=action_id,
            idempotency_key=idempotency_key,
            schema_version="v1",
            timestamp=timestamp,
            deadline=deadline_at,
            component_version="mvp-006",
        )
        inventory = self._gateway.query_inventory(
            {
                "schema_version": "v1",
                "mission_id": mission_request.mission_id,
                "request_id": inventory_request_id,
                "part_id": mission_request.part_id,
                "timestamp": timestamp,
            }
        )
        if (
            inventory.result is not ToolResultKind.SUCCESS
            or inventory.source_location != "Rack A19"
            or inventory.available_quantity < mission_request.quantity
        ):
            raise NormalMissionError("canonical inventory resolution must return Rack A19 with sufficient quantity")

        action_states = [action.status]
        action = action.transition(ActionStatus.EXECUTING, timestamp=timestamp)
        action_states.append(action.status)
        transfer = self._gateway.transfer_part(
            {
                "schema_version": "v1",
                "mission_id": mission_request.mission_id,
                "request_id": transfer_request_id,
                "action_id": action.action_id,
                "idempotency_key": action.idempotency_key,
                "part_id": mission_request.part_id,
                "quantity": mission_request.quantity,
                "source_location": inventory.source_location,
                "destination": mission_request.destination,
                "timestamp": timestamp,
                "deadline_at": deadline_at,
                "timeout_ms": 300_000,
            }
        )
        if transfer.result is not ToolResultKind.SUCCESS or transfer.status is not ActionStatus.SUCCEEDED:
            raise NormalMissionError("canonical normal mission requires a successful Robot Skill observation")
        action = action.transition(ActionStatus.SUCCEEDED, timestamp=timestamp)
        action_states.append(action.status)
        try:
            mission = mission.apply_action_observation(action)
        except StateTransitionError as error:
            raise NormalMissionError("successful normal action must complete the mission") from error
        mission_states.append(mission.status)

        return NormalRun(
            operator_text=operator_text,
            mission_request=mission_request,
            mission=mission,
            action=action,
            inventory=inventory,
            transfer=transfer,
            mission_state_sequence=tuple(mission_states),
            action_state_sequence=tuple(action_states),
            attempted_calls=(
                AttemptedToolCall(
                    request_id=inventory_request_id,
                    action_id=action_id,
                    operation="query_inventory",
                    component_version=inventory.component_version,
                    timestamp=timestamp,
                ),
                AttemptedToolCall(
                    request_id=transfer_request_id,
                    action_id=action_id,
                    operation="transfer_part",
                    component_version=transfer.component_version,
                    timestamp=timestamp,
                ),
            ),
        )


def fixed_runtime_metadata() -> Mapping[str, object]:
    """Return deterministic service-owned metadata for the canonical E2E fixture."""
    return {
        "request_id": "5fca286b-e322-4c1b-ae7b-3b7d1b842d9c",
        "mission_id": "0d47cf1c-31c9-4f80-a8ac-6bd1a8726194",
        "requested_by": "operator",
        "created_at": "2026-08-29T00:00:00Z",
    }
