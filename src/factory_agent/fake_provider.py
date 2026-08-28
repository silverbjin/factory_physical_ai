"""Deterministic semantic test provider for the frozen Day-10 mission."""

from __future__ import annotations

from typing import Mapping

from .service import CANONICAL_MISSION, UnsupportedMissionError


class DeterministicFakeProvider:
    """Returns the same semantic proposal for the one authorized MVP mission."""

    def propose_mission(self, natural_language_mission: str) -> Mapping[str, object]:
        if natural_language_mission != CANONICAL_MISSION:
            raise UnsupportedMissionError("only the frozen canonical mission is supported in MVP-001")
        return {
            "mission_type": "line_side_parts_transfer",
            "part_id": "Brake ECU Type-B",
            "quantity": 1,
            "destination": "Line B",
        }
