"""Finite deterministic state models; no execution adapters or persistence."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import ClassVar
from uuid import UUID


class StateTransitionError(ValueError):
    """Raised when a requested mission or action transition is not permitted."""


class MissionStatus(str, Enum):
    CREATED = "CREATED"
    READY = "READY"
    EXECUTING = "EXECUTING"
    RECONCILING = "RECONCILING"
    RECOVERING = "RECOVERING"
    COMPLETED = "COMPLETED"
    ESCALATED = "ESCALATED"
    FAILED = "FAILED"


class ActionStatus(str, Enum):
    REQUESTED = "REQUESTED"
    EXECUTING = "EXECUTING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    UNKNOWN = "UNKNOWN"
    RECONCILING = "RECONCILING"


def _require_uuid(value: str, field_name: str) -> None:
    try:
        UUID(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{field_name} must be a valid UUID") from error


def _require_non_blank(value: str, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-blank string")


def _require_utc_timestamp(value: str, field_name: str) -> None:
    _require_non_blank(value, field_name)
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        timestamp = datetime.fromisoformat(normalized)
    except ValueError as error:
        raise ValueError(f"{field_name} must be an ISO-8601 UTC timestamp") from error
    if timestamp.tzinfo is None or timestamp.utcoffset() != timedelta(0):
        raise ValueError(f"{field_name} must be an ISO-8601 UTC timestamp")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True, slots=True)
class ActionRecord:
    """A typed physical-action lifecycle record, independent of any adapter."""

    mission_id: str
    action_id: str
    idempotency_key: str
    schema_version: str
    timestamp: str
    deadline: str
    status: ActionStatus = ActionStatus.REQUESTED
    error: str | None = None
    retryable: bool = False
    component_version: str = "mvp-002"

    _TRANSITIONS: ClassVar[dict[ActionStatus, frozenset[ActionStatus]]] = {
        ActionStatus.REQUESTED: frozenset({ActionStatus.EXECUTING}),
        ActionStatus.EXECUTING: frozenset({ActionStatus.SUCCEEDED, ActionStatus.FAILED, ActionStatus.UNKNOWN}),
        ActionStatus.UNKNOWN: frozenset({ActionStatus.RECONCILING}),
        ActionStatus.RECONCILING: frozenset({ActionStatus.FAILED}),
        ActionStatus.SUCCEEDED: frozenset(),
        ActionStatus.FAILED: frozenset(),
    }

    def __post_init__(self) -> None:
        _require_uuid(self.mission_id, "mission_id")
        _require_uuid(self.action_id, "action_id")
        _require_non_blank(self.idempotency_key, "idempotency_key")
        _require_non_blank(self.schema_version, "schema_version")
        _require_utc_timestamp(self.timestamp, "timestamp")
        _require_utc_timestamp(self.deadline, "deadline")
        _require_non_blank(self.component_version, "component_version")
        if not isinstance(self.status, ActionStatus):
            raise ValueError("status must be an ActionStatus")
        if not isinstance(self.retryable, bool):
            raise ValueError("retryable must be a boolean")
        if self.error is not None:
            _require_non_blank(self.error, "error")

    def transition(
        self,
        target: ActionStatus,
        *,
        error: str | None = None,
        retryable: bool = False,
        timestamp: str | None = None,
    ) -> "ActionRecord":
        """Apply a deterministic adapter observation; arbitrary outcomes are rejected."""
        if not isinstance(target, ActionStatus):
            raise StateTransitionError("target must be an ActionStatus")
        if target not in self._TRANSITIONS[self.status]:
            raise StateTransitionError(f"invalid action transition: {self.status.value} -> {target.value}")
        return replace(
            self,
            status=target,
            error=error,
            retryable=retryable,
            timestamp=timestamp or _utc_now(),
        )


@dataclass(frozen=True, slots=True)
class MissionRecord:
    """Finite mission lifecycle driven only by validated action observations."""

    mission_id: str
    status: MissionStatus = MissionStatus.CREATED
    retry_count: int = 0
    retry_limit: int = 1

    _TRANSITIONS: ClassVar[dict[MissionStatus, frozenset[MissionStatus]]] = {
        MissionStatus.CREATED: frozenset({MissionStatus.READY, MissionStatus.ESCALATED}),
        MissionStatus.READY: frozenset({MissionStatus.EXECUTING, MissionStatus.ESCALATED}),
        MissionStatus.EXECUTING: frozenset(
            {MissionStatus.RECONCILING, MissionStatus.COMPLETED, MissionStatus.FAILED, MissionStatus.ESCALATED}
        ),
        MissionStatus.RECONCILING: frozenset(
            {MissionStatus.RECOVERING, MissionStatus.FAILED, MissionStatus.ESCALATED}
        ),
        MissionStatus.RECOVERING: frozenset({MissionStatus.EXECUTING, MissionStatus.FAILED, MissionStatus.ESCALATED}),
        MissionStatus.COMPLETED: frozenset(),
        MissionStatus.ESCALATED: frozenset(),
        MissionStatus.FAILED: frozenset(),
    }

    def __post_init__(self) -> None:
        _require_uuid(self.mission_id, "mission_id")
        if not isinstance(self.status, MissionStatus):
            raise ValueError("status must be a MissionStatus")
        if isinstance(self.retry_count, bool) or not isinstance(self.retry_count, int) or self.retry_count < 0:
            raise ValueError("retry_count must be a non-negative integer")
        if isinstance(self.retry_limit, bool) or not isinstance(self.retry_limit, int) or self.retry_limit < 0:
            raise ValueError("retry_limit must be a non-negative integer")
        if self.retry_count > self.retry_limit:
            raise ValueError("retry_count cannot exceed retry_limit")

    def transition(self, target: MissionStatus) -> "MissionRecord":
        """Transition through the finite table, consuming only the bounded retry."""
        if not isinstance(target, MissionStatus):
            raise StateTransitionError("target must be a MissionStatus")
        if target not in self._TRANSITIONS[self.status]:
            raise StateTransitionError(f"invalid mission transition: {self.status.value} -> {target.value}")
        if self.status is MissionStatus.RECOVERING and target is MissionStatus.EXECUTING:
            if self.retry_count >= self.retry_limit:
                raise StateTransitionError("mission retry limit exhausted")
            return replace(self, status=target, retry_count=self.retry_count + 1)
        return replace(self, status=target)

    def apply_action_observation(self, action: ActionRecord) -> "MissionRecord":
        """Map validated action results to mission states; UNKNOWN is never success."""
        if action.mission_id != self.mission_id:
            raise StateTransitionError("action mission_id does not match mission")
        if self.status is MissionStatus.EXECUTING and action.status is ActionStatus.SUCCEEDED:
            return self.transition(MissionStatus.COMPLETED)
        if self.status is MissionStatus.EXECUTING and action.status is ActionStatus.UNKNOWN:
            return self.transition(MissionStatus.RECONCILING)
        if self.status is MissionStatus.RECONCILING and action.status is ActionStatus.FAILED:
            return self.transition(MissionStatus.RECOVERING if action.retryable else MissionStatus.ESCALATED)
        raise StateTransitionError(
            f"action status {action.status.value} cannot update mission in {self.status.value}"
        )
