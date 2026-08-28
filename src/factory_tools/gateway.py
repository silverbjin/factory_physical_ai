"""Deterministic in-process factory-tool gateway for the Day-10 MVP."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from uuid import UUID

from mission_runtime import ActionStatus


class ToolValidationError(ValueError):
    """Raised when an untrusted factory-tool request violates its schema."""


class ToolResultKind(str, Enum):
    SUCCESS = "success"
    FAILURE = "failure"


class ToolErrorCategory(str, Enum):
    VALIDATION = "VALIDATION"
    RESOURCE_UNAVAILABLE = "RESOURCE_UNAVAILABLE"
    EXECUTION_FAILED = "EXECUTION_FAILED"


@dataclass(frozen=True, slots=True)
class ToolError:
    """Machine-readable failure information returned by a deterministic fake."""

    code: str
    message: str
    category: ToolErrorCategory
    retryable: bool


def _mapping(payload: object, required_fields: frozenset[str], name: str) -> Mapping[str, object]:
    if not isinstance(payload, Mapping):
        raise ToolValidationError(f"{name} must be a mapping")
    if any(not isinstance(key, str) for key in payload):
        raise ToolValidationError(f"{name} keys must be strings")
    fields = set(payload)
    missing = required_fields - fields
    unexpected = fields - required_fields
    if missing or unexpected:
        details: list[str] = []
        if missing:
            details.append(f"missing={sorted(missing)}")
        if unexpected:
            details.append(f"unexpected={sorted(unexpected)}")
        raise ToolValidationError(f"invalid {name} fields: " + ", ".join(details))
    return payload


def _non_blank(values: Mapping[str, object], field_name: str) -> str:
    value = values[field_name]
    if not isinstance(value, str) or not value.strip():
        raise ToolValidationError(f"{field_name} must be a non-blank string")
    return value


def _uuid(values: Mapping[str, object], field_name: str) -> str:
    value = _non_blank(values, field_name)
    try:
        UUID(value)
    except ValueError as error:
        raise ToolValidationError(f"{field_name} must be a valid UUID") from error
    return value


def _utc_timestamp(values: Mapping[str, object], field_name: str) -> str:
    value = _non_blank(values, field_name)
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        timestamp = datetime.fromisoformat(normalized)
    except ValueError as error:
        raise ToolValidationError(f"{field_name} must be an ISO-8601 UTC timestamp") from error
    if timestamp.tzinfo is None or timestamp.utcoffset() != timedelta(0):
        raise ToolValidationError(f"{field_name} must be an ISO-8601 UTC timestamp")
    return value


def _positive_integer(values: Mapping[str, object], field_name: str) -> int:
    value = values[field_name]
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ToolValidationError(f"{field_name} must be a positive integer")
    return value


@dataclass(frozen=True, slots=True)
class InventoryQuery:
    """Strict read-only WMS query envelope for the in-process gateway."""

    schema_version: str
    mission_id: str
    request_id: str
    part_id: str
    timestamp: str

    REQUIRED_FIELDS = frozenset({"schema_version", "mission_id", "request_id", "part_id", "timestamp"})

    @classmethod
    def from_mapping(cls, payload: object) -> "InventoryQuery":
        values = _mapping(payload, cls.REQUIRED_FIELDS, "inventory query")
        schema_version = _non_blank(values, "schema_version")
        if schema_version != "v1":
            raise ToolValidationError("unsupported schema_version")
        return cls(
            schema_version=schema_version,
            mission_id=_uuid(values, "mission_id"),
            request_id=_uuid(values, "request_id"),
            part_id=_non_blank(values, "part_id"),
            timestamp=_utc_timestamp(values, "timestamp"),
        )


@dataclass(frozen=True, slots=True)
class TransferPartRequest:
    """Typed side-effecting Robot Skill request; execution remains fake-only."""

    schema_version: str
    mission_id: str
    request_id: str
    action_id: str
    idempotency_key: str
    part_id: str
    quantity: int
    source_location: str
    destination: str
    timestamp: str
    deadline_at: str
    timeout_ms: int

    REQUIRED_FIELDS = frozenset(
        {
            "schema_version",
            "mission_id",
            "request_id",
            "action_id",
            "idempotency_key",
            "part_id",
            "quantity",
            "source_location",
            "destination",
            "timestamp",
            "deadline_at",
            "timeout_ms",
        }
    )

    @classmethod
    def from_mapping(cls, payload: object) -> "TransferPartRequest":
        values = _mapping(payload, cls.REQUIRED_FIELDS, "transfer request")
        schema_version = _non_blank(values, "schema_version")
        if schema_version != "v1":
            raise ToolValidationError("unsupported schema_version")
        return cls(
            schema_version=schema_version,
            mission_id=_uuid(values, "mission_id"),
            request_id=_uuid(values, "request_id"),
            action_id=_uuid(values, "action_id"),
            idempotency_key=_non_blank(values, "idempotency_key"),
            part_id=_non_blank(values, "part_id"),
            quantity=_positive_integer(values, "quantity"),
            source_location=_non_blank(values, "source_location"),
            destination=_non_blank(values, "destination"),
            timestamp=_utc_timestamp(values, "timestamp"),
            deadline_at=_utc_timestamp(values, "deadline_at"),
            timeout_ms=_positive_integer(values, "timeout_ms"),
        )


@dataclass(frozen=True, slots=True)
class ActionStatusQuery:
    """Strict reconciliation observation query envelope for a known action."""

    schema_version: str
    mission_id: str
    request_id: str
    action_id: str
    timestamp: str

    REQUIRED_FIELDS = frozenset({"schema_version", "mission_id", "request_id", "action_id", "timestamp"})

    @classmethod
    def from_mapping(cls, payload: object) -> "ActionStatusQuery":
        values = _mapping(payload, cls.REQUIRED_FIELDS, "action status query")
        schema_version = _non_blank(values, "schema_version")
        if schema_version != "v1":
            raise ToolValidationError("unsupported schema_version")
        return cls(
            schema_version=schema_version,
            mission_id=_uuid(values, "mission_id"),
            request_id=_uuid(values, "request_id"),
            action_id=_uuid(values, "action_id"),
            timestamp=_utc_timestamp(values, "timestamp"),
        )


@dataclass(frozen=True, slots=True)
class InventoryResult:
    """Typed WMS observation returned by the deterministic inventory fake."""

    result: ToolResultKind
    schema_version: str
    mission_id: str
    request_id: str
    part_id: str
    timestamp: str
    source_location: str | None
    available_quantity: int
    source_kind: str = "mock"
    component_version: str = "mvp-003"
    error: ToolError | None = None


@dataclass(frozen=True, slots=True)
class TransferResult:
    """Typed Robot Skill observation, never a robot command or trajectory."""

    result: ToolResultKind
    schema_version: str
    mission_id: str
    request_id: str
    action_id: str
    idempotency_key: str
    timestamp: str
    deadline_at: str
    timeout_ms: int
    status: ActionStatus
    source_kind: str = "mock"
    component_version: str = "mvp-003"
    error: ToolError | None = None


@dataclass(frozen=True, slots=True)
class ActionStatusResult:
    """Typed query result for a previously submitted fake action."""

    result: ToolResultKind
    schema_version: str
    mission_id: str
    request_id: str
    action_id: str
    timestamp: str
    status: ActionStatus | None
    source_kind: str = "mock"
    component_version: str = "mvp-003"
    error: ToolError | None = None


class DeterministicInventoryFake:
    """Fixture-only WMS fake for the one frozen Day-10 part."""

    _CANONICAL_PART = "Brake ECU Type-B"
    _SOURCE_LOCATION = "Rack A19"

    def query_inventory(self, query: InventoryQuery) -> InventoryResult:
        if query.part_id == self._CANONICAL_PART:
            return InventoryResult(
                result=ToolResultKind.SUCCESS,
                schema_version=query.schema_version,
                mission_id=query.mission_id,
                request_id=query.request_id,
                part_id=query.part_id,
                timestamp=query.timestamp,
                source_location=self._SOURCE_LOCATION,
                available_quantity=1,
            )
        return InventoryResult(
            result=ToolResultKind.FAILURE,
            schema_version=query.schema_version,
            mission_id=query.mission_id,
            request_id=query.request_id,
            part_id=query.part_id,
            timestamp=query.timestamp,
            source_location=None,
            available_quantity=0,
            error=ToolError(
                code="inventory_unavailable",
                message="part is unavailable in the deterministic inventory fixture",
                category=ToolErrorCategory.RESOURCE_UNAVAILABLE,
                retryable=False,
            ),
        )


class DeterministicRobotSkillFake:
    """In-memory typed skill boundary with a constructor-controlled fixture outcome."""

    def __init__(self, fixture_status: ActionStatus = ActionStatus.SUCCEEDED) -> None:
        if fixture_status not in {ActionStatus.SUCCEEDED, ActionStatus.FAILED, ActionStatus.UNKNOWN}:
            raise ToolValidationError("fixture_status must be SUCCEEDED, FAILED, or UNKNOWN")
        self._fixture_status = fixture_status
        self._actions: dict[str, TransferResult] = {}

    def transfer_part(self, request: TransferPartRequest) -> TransferResult:
        existing = self._actions.get(request.action_id)
        if existing is not None:
            return existing
        if self._fixture_status is ActionStatus.SUCCEEDED:
            result = TransferResult(
                result=ToolResultKind.SUCCESS,
                schema_version=request.schema_version,
                mission_id=request.mission_id,
                request_id=request.request_id,
                action_id=request.action_id,
                idempotency_key=request.idempotency_key,
                timestamp=request.timestamp,
                deadline_at=request.deadline_at,
                timeout_ms=request.timeout_ms,
                status=ActionStatus.SUCCEEDED,
            )
        else:
            result = TransferResult(
                result=ToolResultKind.FAILURE,
                schema_version=request.schema_version,
                mission_id=request.mission_id,
                request_id=request.request_id,
                action_id=request.action_id,
                idempotency_key=request.idempotency_key,
                timestamp=request.timestamp,
                deadline_at=request.deadline_at,
                timeout_ms=request.timeout_ms,
                status=self._fixture_status,
                error=ToolError(
                    code="fixture_skill_failure",
                    message="robot skill fixture returned a configured non-success observation",
                    category=ToolErrorCategory.EXECUTION_FAILED,
                    retryable=False,
                ),
            )
        self._actions[request.action_id] = result
        return result

    def get_action_status(self, query: ActionStatusQuery) -> ActionStatusResult:
        action = self._actions.get(query.action_id)
        if action is None:
            return ActionStatusResult(
                result=ToolResultKind.FAILURE,
                schema_version=query.schema_version,
                mission_id=query.mission_id,
                request_id=query.request_id,
                action_id=query.action_id,
                timestamp=query.timestamp,
                status=None,
                error=ToolError(
                    code="action_not_found",
                    message="action is not present in the deterministic skill fixture",
                    category=ToolErrorCategory.RESOURCE_UNAVAILABLE,
                    retryable=False,
                ),
            )
        return ActionStatusResult(
            result=action.result,
            schema_version=query.schema_version,
            mission_id=query.mission_id,
            request_id=query.request_id,
            action_id=query.action_id,
            timestamp=query.timestamp,
            status=action.status,
            error=action.error,
        )


class FactoryToolGateway:
    """Only in-process entry point for typed WMS and Robot Skill fixture calls."""

    def __init__(
        self,
        inventory: DeterministicInventoryFake | None = None,
        robot_skill: DeterministicRobotSkillFake | None = None,
    ) -> None:
        self._inventory = inventory or DeterministicInventoryFake()
        self._robot_skill = robot_skill or DeterministicRobotSkillFake()

    def query_inventory(self, request: object) -> InventoryResult:
        query = InventoryQuery.from_mapping(request)
        return self._inventory.query_inventory(query)

    def transfer_part(self, request: object) -> TransferResult:
        transfer = TransferPartRequest.from_mapping(request)
        return self._robot_skill.transfer_part(transfer)

    def get_action_status(self, request: object) -> ActionStatusResult:
        query = ActionStatusQuery.from_mapping(request)
        return self._robot_skill.get_action_status(query)
