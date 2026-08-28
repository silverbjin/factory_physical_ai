"""Validated natural-language to structured-mission boundary."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import datetime, timezone
from uuid import uuid4

from contracts import MissionProposal, MissionRequest

from .provider import MissionProvider

CANONICAL_MISSION = "Line B에 Brake ECU Type-B 1개를 공급해줘."
RuntimeMetadataFactory = Callable[[], Mapping[str, object]]


class UnsupportedMissionError(ValueError):
    """Raised when the frozen MVP accepts no semantic interpretation for a request."""


def _runtime_metadata() -> dict[str, object]:
    """Create service-owned metadata; providers never invent these fields."""
    return {
        "request_id": str(uuid4()),
        "mission_id": str(uuid4()),
        "requested_by": "operator",
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }


class FactoryAgent:
    """Converts a provider proposal into a validated mission; performs no execution."""

    def __init__(
        self,
        provider: MissionProvider,
        runtime_metadata_factory: RuntimeMetadataFactory = _runtime_metadata,
    ) -> None:
        self._provider = provider
        self._runtime_metadata_factory = runtime_metadata_factory

    def parse_mission(self, natural_language_mission: str) -> MissionRequest:
        proposal = MissionProposal.from_mapping(self._provider.propose_mission(natural_language_mission))
        metadata = self._runtime_metadata_factory()
        return MissionRequest.from_mapping(
            {
                "schema_version": "v1",
                "request_id": metadata.get("request_id"),
                "mission_id": metadata.get("mission_id"),
                "mission_type": proposal.mission_type,
                "part_id": proposal.part_id,
                "quantity": proposal.quantity,
                "destination": proposal.destination,
                "requested_by": metadata.get("requested_by"),
                "created_at": metadata.get("created_at"),
            }
        )
