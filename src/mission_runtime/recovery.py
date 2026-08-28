"""Deterministic MVP-004 timeout reconciliation and one-retry coordinator."""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from factory_tools.gateway import DeterministicTimeoutRecoverySkillFake, FactoryToolGateway, ToolResultKind

from .state import ActionRecord, ActionStatus, MissionRecord, MissionStatus, StateTransitionError


@dataclass(frozen=True, slots=True)
class RecoveryRun:
    """Observed result of the one approved Day-10 failure/recovery path."""

    mission: MissionRecord
    first_action: ActionRecord
    retry_action: ActionRecord | None
    call_trace: tuple[str, ...]
    reconciliation_retryable: bool
    mission_state_sequence: tuple[MissionStatus, ...]
    first_action_state_sequence: tuple[ActionStatus, ...]


class SingleFailureRecoveryCoordinator:
    """Runtime-owned policy: timeout -> reconcile -> at most one retry or escalate."""

    _RETRY_BUDGET: ClassVar[int] = 1

    def __init__(self, gateway: FactoryToolGateway) -> None:
        self._gateway = gateway

    def run(
        self,
        *,
        mission_id: str,
        idempotency_key: str,
        first_action_id: str,
        retry_action_id: str,
        request_ids: tuple[str, str, str],
        timestamp: str,
        deadline_at: str,
    ) -> RecoveryRun:
        """Run only the frozen timeout scenario; callers cannot supply retry policy."""
        mission = MissionRecord(mission_id)
        mission_states = [mission.status]
        mission = mission.transition(MissionStatus.READY)
        mission_states.append(mission.status)
        mission = mission.transition(MissionStatus.EXECUTING)
        mission_states.append(mission.status)
        first_action = self._action(mission_id, first_action_id, idempotency_key, timestamp, deadline_at)
        first_action_states = [first_action.status]
        first_result = self._gateway.transfer_part(
            self._transfer_request(mission_id, request_ids[0], first_action_id, idempotency_key, timestamp, deadline_at)
        )
        if first_result.status is not ActionStatus.UNKNOWN:
            raise StateTransitionError("MVP-004 requires the first Robot Skill result to be UNKNOWN")
        first_action = first_action.transition(
            ActionStatus.EXECUTING, timestamp=timestamp
        )
        first_action_states.append(first_action.status)
        first_action = first_action.transition(ActionStatus.UNKNOWN, error="robot_skill_timeout", timestamp=timestamp)
        first_action_states.append(first_action.status)
        mission = mission.apply_action_observation(first_action)
        mission_states.append(mission.status)

        reconciled = self._gateway.get_action_status(
            {
                "schema_version": "v1",
                "mission_id": mission_id,
                "request_id": request_ids[1],
                "action_id": first_action_id,
                "timestamp": timestamp,
            }
        )
        if reconciled.status is not ActionStatus.FAILED or reconciled.error is None:
            raise StateTransitionError("reconciliation must return a typed FAILED observation")
        first_action = first_action.transition(
            ActionStatus.RECONCILING, timestamp=timestamp
        )
        first_action_states.append(first_action.status)
        first_action = first_action.transition(
            ActionStatus.FAILED,
            error=reconciled.error.code,
            retryable=reconciled.error.retryable,
            timestamp=timestamp,
        )
        first_action_states.append(first_action.status)
        mission = mission.apply_action_observation(first_action)
        mission_states.append(mission.status)
        if mission.status is MissionStatus.ESCALATED:
            return RecoveryRun(
                mission=mission,
                first_action=first_action,
                retry_action=None,
                call_trace=self._trace(),
                reconciliation_retryable=False,
                mission_state_sequence=tuple(mission_states),
                first_action_state_sequence=tuple(first_action_states),
            )
        if mission.status is not MissionStatus.RECOVERING or not reconciled.error.retryable:
            raise StateTransitionError("only a retryable reconciled failure may enter recovery")

        mission = mission.transition(MissionStatus.EXECUTING)
        mission_states.append(mission.status)
        retry_action = self._action(mission_id, retry_action_id, idempotency_key, timestamp, deadline_at)
        retry_result = self._gateway.transfer_part(
            self._transfer_request(mission_id, request_ids[2], retry_action_id, idempotency_key, timestamp, deadline_at)
        )
        if retry_result.result is not ToolResultKind.SUCCESS or retry_result.status is not ActionStatus.SUCCEEDED:
            raise StateTransitionError("the approved recovery retry must succeed")
        retry_action = retry_action.transition(
            ActionStatus.EXECUTING, timestamp=timestamp
        ).transition(ActionStatus.SUCCEEDED, timestamp=timestamp)
        mission = mission.apply_action_observation(retry_action)
        mission_states.append(mission.status)
        return RecoveryRun(
            mission=mission,
            first_action=first_action,
            retry_action=retry_action,
            call_trace=self._trace(),
            reconciliation_retryable=True,
            mission_state_sequence=tuple(mission_states),
            first_action_state_sequence=tuple(first_action_states),
        )

    @staticmethod
    def _action(
        mission_id: str, action_id: str, idempotency_key: str, timestamp: str, deadline_at: str
    ) -> ActionRecord:
        return ActionRecord(
            mission_id=mission_id,
            action_id=action_id,
            idempotency_key=idempotency_key,
            schema_version="v1",
            timestamp=timestamp,
            deadline=deadline_at,
            component_version="mvp-004",
        )

    @staticmethod
    def _transfer_request(
        mission_id: str,
        request_id: str,
        action_id: str,
        idempotency_key: str,
        timestamp: str,
        deadline_at: str,
    ) -> dict[str, object]:
        return {
            "schema_version": "v1",
            "mission_id": mission_id,
            "request_id": request_id,
            "action_id": action_id,
            "idempotency_key": idempotency_key,
            "part_id": "Brake ECU Type-B",
            "quantity": 1,
            "source_location": "Rack A19",
            "destination": "Line B",
            "timestamp": timestamp,
            "deadline_at": deadline_at,
            "timeout_ms": 300_000,
        }

    def _trace(self) -> tuple[str, ...]:
        skill = self._gateway._robot_skill
        if not isinstance(skill, DeterministicTimeoutRecoverySkillFake):
            raise StateTransitionError("MVP-004 requires the deterministic timeout recovery fixture")
        return tuple(skill.call_trace)
