"""Fail-closed contracts for the Day-10 Factory Agent boundary."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from uuid import UUID


class MissionValidationError(ValueError):
    """Raised when an untrusted proposal or mission request is invalid."""


def _validated_mapping(payload: object, required_fields: frozenset[str]) -> Mapping[str, object]:
    if not isinstance(payload, Mapping):
        raise MissionValidationError("mission payload must be a mapping")
    if any(not isinstance(key, str) for key in payload):
        raise MissionValidationError("mission payload keys must be strings")

    fields = set(payload)
    missing = required_fields - fields
    unexpected = fields - required_fields
    if missing or unexpected:
        details = []
        if missing:
            details.append(f"missing={sorted(missing)}")
        if unexpected:
            details.append(f"unexpected={sorted(unexpected)}")
        raise MissionValidationError("invalid mission fields: " + ", ".join(details))
    return payload


def _required_string(values: Mapping[str, object], field_name: str) -> str:
    value = values[field_name]
    if not isinstance(value, str) or not value.strip():
        raise MissionValidationError(f"{field_name} must be a non-blank string")
    return value


def _positive_quantity(values: Mapping[str, object]) -> int:
    quantity = values["quantity"]
    if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity <= 0:
        raise MissionValidationError("quantity must be a positive integer")
    return quantity


def _uuid(values: Mapping[str, object], field_name: str) -> str:
    value = _required_string(values, field_name)
    try:
        UUID(value)
    except ValueError as error:
        raise MissionValidationError(f"{field_name} must be a valid UUID") from error
    return value


def _utc_timestamp(values: Mapping[str, object], field_name: str) -> str:
    value = _required_string(values, field_name)
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        timestamp = datetime.fromisoformat(normalized)
    except ValueError as error:
        raise MissionValidationError(f"{field_name} must be an ISO-8601 UTC timestamp") from error
    if timestamp.tzinfo is None or timestamp.utcoffset() != timedelta(0):
        raise MissionValidationError(f"{field_name} must be an ISO-8601 UTC timestamp")
    return value


@dataclass(frozen=True, slots=True)
class MissionProposal:
    """Semantic fields proposed by a provider and validated before use."""

    mission_type: str
    part_id: str
    quantity: int
    destination: str

    REQUIRED_FIELDS = frozenset({"mission_type", "part_id", "quantity", "destination"})

    @classmethod
    def from_mapping(cls, payload: object) -> "MissionProposal":
        values = _validated_mapping(payload, cls.REQUIRED_FIELDS)
        mission_type = _required_string(values, "mission_type")
        if mission_type != "line_side_parts_transfer":
            raise MissionValidationError("unsupported mission_type")
        return cls(
            mission_type=mission_type,
            part_id=_required_string(values, "part_id"),
            quantity=_positive_quantity(values),
            destination=_required_string(values, "destination"),
        )

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class MissionRequest:
    """Validated outer mission boundary built by deterministic application code."""

    schema_version: str
    request_id: str
    mission_id: str
    mission_type: str
    part_id: str
    quantity: int
    destination: str
    requested_by: str
    created_at: str

    REQUIRED_FIELDS = frozenset(
        {
            "schema_version",
            "request_id",
            "mission_id",
            "mission_type",
            "part_id",
            "quantity",
            "destination",
            "requested_by",
            "created_at",
        }
    )

    @classmethod
    def from_mapping(cls, payload: object) -> "MissionRequest":
        values = _validated_mapping(payload, cls.REQUIRED_FIELDS)
        schema_version = _required_string(values, "schema_version")
        if schema_version != "v1":
            raise MissionValidationError("unsupported schema_version")

        proposal = MissionProposal.from_mapping(
            {
                "mission_type": values["mission_type"],
                "part_id": values["part_id"],
                "quantity": values["quantity"],
                "destination": values["destination"],
            }
        )
        return cls(
            schema_version=schema_version,
            request_id=_uuid(values, "request_id"),
            mission_id=_uuid(values, "mission_id"),
            mission_type=proposal.mission_type,
            part_id=proposal.part_id,
            quantity=proposal.quantity,
            destination=proposal.destination,
            requested_by=_required_string(values, "requested_by"),
            created_at=_utc_timestamp(values, "created_at"),
        )

    def to_dict(self) -> dict[str, object]:
        return asdict(self)
