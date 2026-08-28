"""Provider boundary: semantic output only, never an execution command."""

from __future__ import annotations

from typing import Protocol


class MissionProvider(Protocol):
    def propose_mission(self, natural_language_mission: str) -> object:
        """Return an untrusted structured mission proposal for validation."""
