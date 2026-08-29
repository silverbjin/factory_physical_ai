"""Canonical Agent/WMS plus frozen timeout-recovery E2E composition for MVP-007."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from contracts import MissionRequest
from factory_agent import FactoryAgent
from factory_tools import FactoryToolGateway, InventoryResult, ToolResultKind

from .persistence import RunArtifacts
from .recovery import AttemptedToolCall, RecoveryRun, SingleFailureRecoveryCoordinator


class FailureRecoveryMissionError(ValueError):
    """Raised when the only approved failure-recovery E2E run violates its invariant."""


@dataclass(frozen=True, slots=True)
class FailureRecoveryE2ERun:
    """Canonical mission input, successful inventory observation, and recovery result."""

    operator_text: str
    mission_request: MissionRequest
    inventory: InventoryResult
    inventory_call: AttemptedToolCall
    recovery: RecoveryRun


class CanonicalFailureRecoveryE2EExecutor:
    """Composes the existing safe boundaries without adding a second failure policy."""

    def __init__(self, agent: FactoryAgent, gateway: FactoryToolGateway) -> None:
        self._agent = agent
        self._gateway = gateway
        self._recovery = SingleFailureRecoveryCoordinator(gateway)

    def run(
        self,
        operator_text: str,
        *,
        inventory_request_id: str,
        recovery_request_ids: tuple[str, str, str],
        first_action_id: str,
        retry_action_id: str,
        idempotency_key: str,
        timestamp: str,
        deadline_at: str,
    ) -> FailureRecoveryE2ERun:
        """Run exactly one inventory success, timeout, reconciliation, and retry success."""
        mission_request = self._agent.parse_mission(operator_text)
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
            raise FailureRecoveryMissionError("canonical inventory resolution must precede recovery")
        recovery = self._recovery.run(
            mission_id=mission_request.mission_id,
            idempotency_key=idempotency_key,
            first_action_id=first_action_id,
            retry_action_id=retry_action_id,
            request_ids=recovery_request_ids,
            timestamp=timestamp,
            deadline_at=deadline_at,
        )
        if recovery.mission.mission_id != mission_request.mission_id:
            raise FailureRecoveryMissionError("recovery mission correlation is invalid")
        return FailureRecoveryE2ERun(
            operator_text=operator_text,
            mission_request=mission_request,
            inventory=inventory,
            inventory_call=AttemptedToolCall(
                request_id=inventory_request_id,
                action_id=first_action_id,
                operation="query_inventory",
                component_version=inventory.component_version,
                timestamp=timestamp,
            ),
            recovery=recovery,
        )


def write_failure_recovery_e2e_latest(
    run: FailureRecoveryE2ERun,
    artifacts: RunArtifacts,
    output_path: Path,
) -> Path:
    """Write the E2E evidence wrapper around the durable MVP-005 recovery artifacts."""
    _validate_failure_recovery_e2e(run, artifacts)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        **artifacts.summary,
        "operator_text": run.operator_text,
        "part_id": run.mission_request.part_id,
        "quantity": run.mission_request.quantity,
        "destination": run.mission_request.destination,
        "inventory": {
            "request_id": run.inventory_call.request_id,
            "source_location": run.inventory.source_location,
            "available_quantity": run.inventory.available_quantity,
            "source_kind": run.inventory.source_kind,
            "component_version": run.inventory.component_version,
        },
        "logical_transfer_count": 2,
        "extra_execution_count": 0,
        "artifact_paths": {
            "sqlite": str(artifacts.database_path),
            "trace_jsonl": str(artifacts.trace_path),
            "summary_json": str(artifacts.summary_path),
        },
    }
    with output_path.open("w", encoding="utf-8") as output_file:
        json.dump(payload, output_file, indent=2, sort_keys=True)
        output_file.write("\n")
    return output_path


def _validate_failure_recovery_e2e(run: FailureRecoveryE2ERun, artifacts: RunArtifacts) -> None:
    """Fail closed unless WMS context and recovery artifacts describe the same frozen run."""
    request = run.mission_request
    recovery = run.recovery
    summary = artifacts.summary
    if (
        run.operator_text != "Line B에 Brake ECU Type-B 1개를 공급해줘."
        or request.part_id != "Brake ECU Type-B"
        or request.quantity != 1
        or request.destination != "Line B"
        or run.inventory.result is not ToolResultKind.SUCCESS
        or run.inventory.source_location != "Rack A19"
        or run.inventory.mission_id != request.mission_id
        or run.inventory.request_id != run.inventory_call.request_id
        or run.inventory.component_version != run.inventory_call.component_version
        or run.inventory.timestamp != run.inventory_call.timestamp
        or run.inventory_call.operation != "query_inventory"
        or recovery.mission.mission_id != request.mission_id
        or recovery.first_action.mission_id != request.mission_id
        or recovery.retry_action is None
        or recovery.retry_action.mission_id != request.mission_id
        or recovery.first_action.action_id != run.inventory_call.action_id
        or summary.get("run_id") != artifacts.run_id
        or summary.get("mission_id") != request.mission_id
        or summary.get("action_ids") != [recovery.first_action.action_id, recovery.retry_action.action_id]
        or summary.get("mission_result") != "COMPLETED"
        or summary.get("timeout_detected") is not True
        or summary.get("reconciliation_performed") is not True
        or summary.get("retry_budget") != 1
        or summary.get("retry_count") != 1
        or summary.get("recovery_result") != "SUCCEEDED"
    ):
        raise FailureRecoveryMissionError("failure-recovery E2E evidence correlation is invalid")
