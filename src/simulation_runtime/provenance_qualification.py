"""Fail-closed models for additive simulation provenance qualification."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

RECORD_KINDS = frozenset({"operation_run", "profile_aggregate", "version_qualification"})
_FAKE = frozenset({"", "not_applicable", "N/A", "unknown", "placeholder"})


@dataclass(frozen=True)
class QualificationSubject:
    subject_id: str
    record_kind: str
    claim_scope: str
    predecessor_binding: Mapping[str, Any]
    qualification_run_id: str | None
    scenario_id: str | None
    backend_id: str
    component_version: str
    configuration_provenance: Mapping[str, str]
    world_model_provenance: Mapping[str, str]
    timing: Mapping[str, Any] | None
    semantic_outcome: Mapping[str, Any] | None
    profile_id: str | None = None
    correlation_identity: Mapping[str, str] | None = None


def _require(value: Any, reason: str) -> None:
    if value in _FAKE:
        raise ValueError("FAKE_NOT_APPLICABLE")
    if value is None:
        raise ValueError(reason)


def _hashes(values: Mapping[str, str], reason: str) -> None:
    if not values:
        raise ValueError(reason)
    for value in values.values():
        if not isinstance(value, str) or len(value) != 64 or value in _FAKE:
            raise ValueError(reason)


def validate_subject(subject: QualificationSubject) -> None:
    """Validate only explicit, applicable qualification facts."""
    _require(subject.subject_id, "MISSING_SUBJECT_ID")
    if subject.record_kind not in RECORD_KINDS:
        raise ValueError("INVALID_RECORD_KIND")
    if subject.claim_scope not in {"run_local", "profile", "version"}:
        raise ValueError("INVALID_CLAIM_SCOPE")
    binding = subject.predecessor_binding
    for field in ("task_id", "accepted_commit", "evidence_path", "evidence_sha256"):
        _require(binding.get(field), f"MISSING_PREDECESSOR_{field.upper()}")
    if len(str(binding["accepted_commit"])) != 40 or len(str(binding["evidence_sha256"])) != 64:
        raise ValueError("INVALID_PREDECESSOR_BINDING")
    _require(subject.backend_id, "MISSING_BACKEND")
    _require(subject.component_version, "MISSING_COMPONENT_VERSION")
    _hashes(subject.configuration_provenance, "MISSING_CONFIGURATION_PROVENANCE")
    _hashes(subject.world_model_provenance, "MISSING_WORLD_MODEL_PROVENANCE")
    if len(set(subject.configuration_provenance.values())) != len(subject.configuration_provenance):
        raise ValueError("SEMANTIC_HASH_ALIAS")
    if subject.record_kind == "operation_run":
        _require(subject.qualification_run_id, "MISSING_QUALIFICATION_RUN_ID")
        _require(subject.scenario_id, "MISSING_SCENARIO_ID")
        if not isinstance(subject.timing, Mapping) or not isinstance(subject.timing.get("simulation_time"), (int, float)):
            raise ValueError("MISSING_STRUCTURED_SIMULATION_TIME")
        if not isinstance(subject.semantic_outcome, Mapping):
            raise ValueError("MISSING_SEMANTIC_OUTCOME")
    elif subject.record_kind == "profile_aggregate":
        _require(subject.profile_id, "MISSING_PROFILE_ID")
        if subject.qualification_run_id is not None or subject.scenario_id is not None:
            raise ValueError("AGGREGATE_OPERATION_IMPERSONATION")
    else:
        if subject.claim_scope != "version" or subject.qualification_run_id is not None:
            raise ValueError("INVALID_VERSION_QUALIFICATION")
