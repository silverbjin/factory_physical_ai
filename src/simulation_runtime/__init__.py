"""Bounded deterministic Simulation Lane smoke runtime."""

from typing import Any

from .smoke import ContractViolation, canonical_sha256, run_smoke_suite, validate_contract_message

__all__ = (
    "ContractViolation",
    "canonical_sha256",
    "run_smoke_suite",
    "validate_contract_message",
    "MissionIntegrationRuntime",
    "ProfileUnavailable",
    "PROFILES",
    "select_profile",
)


def __getattr__(name: str) -> Any:
    """Load profile integration only for callers that explicitly request it."""
    if name in {"MissionIntegrationRuntime", "ProfileUnavailable", "PROFILES", "select_profile"}:
        from . import mission_integration

        return getattr(mission_integration, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
