"""SQLite lifecycle persistence and JSONL evidence for the single Day-10 run."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from uuid import UUID

from .recovery import AttemptedToolCall, RecoveryRun
from .state import ActionRecord, ActionStatus, MissionStatus


class PersistenceValidationError(ValueError):
    """Raised when a persistence/evidence request violates the frozen MVP profile."""


@dataclass(frozen=True, slots=True)
class PersistedActionState:
    """A reloaded immutable action state from one durable transition."""

    mission_id: str
    action_id: str
    idempotency_key: str
    status: ActionStatus
    timestamp: str
    error: str | None
    retryable: bool


@dataclass(frozen=True, slots=True)
class RunArtifacts:
    """Local paths and machine-readable summary for one deterministic MVP run."""

    run_id: str
    database_path: Path
    trace_path: Path
    summary_path: Path
    summary: dict[str, object]


def _utc_timestamp(value: str, field_name: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise PersistenceValidationError(f"{field_name} must be a non-blank ISO-8601 UTC timestamp")
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as error:
        raise PersistenceValidationError(f"{field_name} must be a non-blank ISO-8601 UTC timestamp") from error
    if parsed.tzinfo is None or parsed.utcoffset() != timedelta(0):
        raise PersistenceValidationError(f"{field_name} must be a non-blank ISO-8601 UTC timestamp")
    return parsed


def _identifier(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PersistenceValidationError(f"{field_name} must be a non-blank string")
    return value


def _uuid(value: str, field_name: str) -> str:
    identifier = _identifier(value, field_name)
    try:
        UUID(identifier)
    except ValueError as error:
        raise PersistenceValidationError(f"{field_name} must be a valid UUID") from error
    return identifier


class MissionLifecycleStore:
    """Single-process SQLite store for one recovered canonical mission lifecycle."""

    def __init__(self, database_path: Path) -> None:
        self._database_path = database_path
        self._database_path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(self._database_path)
        self._connection.row_factory = sqlite3.Row
        self.create_schema()

    def close(self) -> None:
        self._connection.close()

    def create_schema(self) -> None:
        self._connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS runs (
                run_id TEXT PRIMARY KEY,
                mission_id TEXT NOT NULL,
                mission_result TEXT NOT NULL,
                tool_call_valid INTEGER NOT NULL,
                timeout_detected INTEGER NOT NULL,
                reconciliation_performed INTEGER NOT NULL,
                retry_budget INTEGER NOT NULL,
                retry_count INTEGER NOT NULL,
                recovery_result TEXT NOT NULL,
                hitl_escalated INTEGER NOT NULL,
                mission_duration_ms INTEGER NOT NULL,
                error_category TEXT,
                component_versions_json TEXT NOT NULL,
                started_at TEXT NOT NULL,
                completed_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS missions (
                run_id TEXT PRIMARY KEY REFERENCES runs(run_id),
                mission_id TEXT NOT NULL,
                final_status TEXT NOT NULL,
                retry_count INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS actions (
                run_id TEXT NOT NULL REFERENCES runs(run_id),
                action_id TEXT NOT NULL,
                mission_id TEXT NOT NULL,
                idempotency_key TEXT NOT NULL,
                final_status TEXT NOT NULL,
                deadline_at TEXT NOT NULL,
                component_version TEXT NOT NULL,
                PRIMARY KEY (run_id, action_id)
            );
            CREATE TABLE IF NOT EXISTS mission_transitions (
                run_id TEXT NOT NULL REFERENCES runs(run_id),
                ordinal INTEGER NOT NULL,
                status TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                PRIMARY KEY (run_id, ordinal)
            );
            CREATE TABLE IF NOT EXISTS action_transitions (
                run_id TEXT NOT NULL REFERENCES runs(run_id),
                action_id TEXT NOT NULL,
                ordinal INTEGER NOT NULL,
                status TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                error TEXT,
                retryable INTEGER NOT NULL,
                PRIMARY KEY (run_id, action_id, ordinal)
            );
            CREATE TABLE IF NOT EXISTS attempted_calls (
                run_id TEXT NOT NULL REFERENCES runs(run_id),
                ordinal INTEGER NOT NULL,
                request_id TEXT NOT NULL,
                action_id TEXT NOT NULL,
                operation TEXT NOT NULL,
                component_version TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                PRIMARY KEY (run_id, ordinal)
            );
            CREATE TABLE IF NOT EXISTS events (
                run_id TEXT NOT NULL REFERENCES runs(run_id),
                ordinal INTEGER NOT NULL,
                event_type TEXT NOT NULL,
                action_id TEXT,
                payload_json TEXT NOT NULL,
                PRIMARY KEY (run_id, ordinal)
            );
            """
        )
        self._connection.commit()

    def persist_recovery_run(
        self,
        run: RecoveryRun,
        *,
        run_id: str,
        started_at: str,
        completed_at: str,
    ) -> dict[str, object]:
        """Persist the one accepted timeout/reconciliation/retry lifecycle atomically."""
        _identifier(run_id, "run_id")
        started = _utc_timestamp(started_at, "started_at")
        completed = _utc_timestamp(completed_at, "completed_at")
        if completed < started:
            raise PersistenceValidationError("completed_at must not precede started_at")
        if run.mission.status is not MissionStatus.COMPLETED or run.retry_action is None:
            raise PersistenceValidationError("MVP-005 records only the completed canonical recovery run")
        if run.first_action.status is not ActionStatus.FAILED or run.retry_action.status is not ActionStatus.SUCCEEDED:
            raise PersistenceValidationError("canonical recovery action statuses are required")
        if run.mission.retry_count != 1:
            raise PersistenceValidationError("canonical recovery must consume exactly one retry")
        if ActionStatus.UNKNOWN not in run.first_action_state_sequence:
            raise PersistenceValidationError("canonical recovery must persist an UNKNOWN action transition")
        if MissionStatus.RECONCILING not in run.mission_state_sequence:
            raise PersistenceValidationError("canonical recovery must persist reconciliation")

        duration_ms = int((completed - started).total_seconds() * 1000)
        actions = (run.first_action, run.retry_action)
        attempted_calls = self._validated_attempted_calls(run)
        tool_call_valid = True
        first_states = run.first_action_state_sequence
        retry_states = (ActionStatus.REQUESTED, ActionStatus.EXECUTING, ActionStatus.SUCCEEDED)
        summary = {
            "schema_version": "v1",
            "run_id": run_id,
            "mission_id": run.mission.mission_id,
            "action_ids": [action.action_id for action in actions],
            "attempted_calls": [self._call_dict(call) for call in attempted_calls],
            "mission_result": run.mission.status.value,
            "tool_call_valid": tool_call_valid,
            "state_transitions": {
                "mission": [state.value for state in run.mission_state_sequence],
                "actions": {
                    run.first_action.action_id: [state.value for state in first_states],
                    run.retry_action.action_id: [state.value for state in retry_states],
                },
            },
            "timeout_detected": True,
            "reconciliation_performed": True,
            "retry_budget": 1,
            "retry_count": run.mission.retry_count,
            "recovery_result": run.retry_action.status.value,
            "hitl_escalated": False,
            "mission_duration_ms": duration_ms,
            "error_category": "DEPENDENCY_TIMEOUT",
            "component_versions": {
                "mission_runtime": "mvp-005",
                "recovery_coordinator": "mvp-004",
                "factory_tool_gateway": "mvp-003",
            },
            "started_at": started_at,
            "completed_at": completed_at,
        }
        events = self._events(run, run_id, attempted_calls, started_at, completed_at)
        with self._connection:
            self._connection.execute(
                """INSERT INTO runs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    run_id,
                    run.mission.mission_id,
                    run.mission.status.value,
                    int(tool_call_valid),
                    1,
                    1,
                    1,
                    run.mission.retry_count,
                    run.retry_action.status.value,
                    0,
                    duration_ms,
                    "DEPENDENCY_TIMEOUT",
                    json.dumps(summary["component_versions"], sort_keys=True),
                    started_at,
                    completed_at,
                ),
            )
            self._connection.execute(
                "INSERT INTO missions VALUES (?, ?, ?, ?)",
                (run_id, run.mission.mission_id, run.mission.status.value, run.mission.retry_count),
            )
            for action in actions:
                self._connection.execute(
                    "INSERT INTO actions VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (
                        run_id,
                        action.action_id,
                        action.mission_id,
                        action.idempotency_key,
                        action.status.value,
                        action.deadline,
                        action.component_version,
                    ),
                )
            for ordinal, status in enumerate(run.mission_state_sequence):
                self._connection.execute(
                    "INSERT INTO mission_transitions VALUES (?, ?, ?, ?)",
                    (run_id, ordinal, status.value, completed_at),
                )
            self._persist_action_states(run_id, run.first_action, first_states, completed_at)
            self._persist_action_states(run_id, run.retry_action, retry_states, completed_at)
            for ordinal, call in enumerate(attempted_calls):
                self._connection.execute(
                    "INSERT INTO attempted_calls VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (
                        run_id,
                        ordinal,
                        call.request_id,
                        call.action_id,
                        call.operation,
                        call.component_version,
                        call.timestamp,
                    ),
                )
            for ordinal, event in enumerate(events):
                self._connection.execute(
                    "INSERT INTO events VALUES (?, ?, ?, ?, ?)",
                    (run_id, ordinal, event["event_type"], event.get("action_id"), json.dumps(event, sort_keys=True)),
                )
        return summary

    @staticmethod
    def _call_dict(call: AttemptedToolCall) -> dict[str, str]:
        return {
            "request_id": call.request_id,
            "action_id": call.action_id,
            "operation": call.operation,
            "component_version": call.component_version,
            "timestamp": call.timestamp,
        }

    @staticmethod
    def _validated_attempted_calls(run: RecoveryRun) -> tuple[AttemptedToolCall, ...]:
        expected = (
            (run.first_action.action_id, "transfer_part"),
            (run.first_action.action_id, "get_action_status"),
            (run.retry_action.action_id, "transfer_part"),
        )
        if len(run.attempted_calls) != len(expected):
            raise PersistenceValidationError("canonical recovery requires exactly three attempted tool calls")
        for call, (action_id, operation) in zip(run.attempted_calls, expected, strict=True):
            _uuid(call.request_id, "request_id")
            if call.action_id != action_id or call.operation != operation:
                raise PersistenceValidationError("attempted tool call does not match the canonical recovery trace")
            _identifier(call.component_version, "component_version")
            _utc_timestamp(call.timestamp, "attempted_call.timestamp")
        return run.attempted_calls

    def _persist_action_states(
        self, run_id: str, action: ActionRecord, states: tuple[ActionStatus, ...], timestamp: str
    ) -> None:
        for ordinal, status in enumerate(states):
            is_final = ordinal == len(states) - 1
            self._connection.execute(
                "INSERT INTO action_transitions VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    run_id,
                    action.action_id,
                    ordinal,
                    status.value,
                    timestamp,
                    action.error if is_final else None,
                    int(action.retryable if is_final else False),
                ),
            )

    @staticmethod
    def _events(
        run: RecoveryRun,
        run_id: str,
        attempted_calls: tuple[AttemptedToolCall, ...],
        started_at: str,
        completed_at: str,
    ) -> tuple[dict[str, object], ...]:
        timeout_call, reconciliation_call, recovery_call = attempted_calls
        return (
            {
                "schema_version": "v1",
                "run_id": run_id,
                "mission_id": run.mission.mission_id,
                **MissionLifecycleStore._call_dict(timeout_call),
                "event_type": "timeout_detected",
                "timestamp": started_at,
                "status": ActionStatus.UNKNOWN.value,
                "error_category": "DEPENDENCY_TIMEOUT",
            },
            {
                "schema_version": "v1",
                "run_id": run_id,
                "mission_id": run.mission.mission_id,
                **MissionLifecycleStore._call_dict(reconciliation_call),
                "event_type": "reconciliation_performed",
                "timestamp": completed_at,
                "status": ActionStatus.FAILED.value,
                "retryable": run.reconciliation_retryable,
            },
            {
                "schema_version": "v1",
                "run_id": run_id,
                "mission_id": run.mission.mission_id,
                **MissionLifecycleStore._call_dict(recovery_call),
                "event_type": "recovery_completed",
                "timestamp": completed_at,
                "status": run.mission.status.value,
                "retry_count": run.mission.retry_count,
            },
        )

    def load_action_state(self, run_id: str, action_id: str, ordinal: int) -> PersistedActionState:
        """Reload one persisted state without applying any state interpretation."""
        row = self._connection.execute(
            """
            SELECT actions.mission_id, actions.action_id, actions.idempotency_key,
                   action_transitions.status, action_transitions.timestamp,
                   action_transitions.error, action_transitions.retryable
            FROM actions JOIN action_transitions
              ON actions.run_id = action_transitions.run_id AND actions.action_id = action_transitions.action_id
            WHERE actions.run_id = ? AND actions.action_id = ? AND action_transitions.ordinal = ?
            """,
            (run_id, action_id, ordinal),
        ).fetchone()
        if row is None:
            raise PersistenceValidationError("persisted action state was not found")
        return PersistedActionState(
            mission_id=row["mission_id"],
            action_id=row["action_id"],
            idempotency_key=row["idempotency_key"],
            status=ActionStatus(row["status"]),
            timestamp=row["timestamp"],
            error=row["error"],
            retryable=bool(row["retryable"]),
        )

    def load_summary(self, run_id: str) -> dict[str, object]:
        row = self._connection.execute("SELECT * FROM runs WHERE run_id = ?", (run_id,)).fetchone()
        if row is None:
            raise PersistenceValidationError("persisted run was not found")
        actions = self._connection.execute(
            "SELECT action_id FROM actions WHERE run_id = ? ORDER BY rowid", (run_id,)
        ).fetchall()
        mission_states = self._connection.execute(
            "SELECT status FROM mission_transitions WHERE run_id = ? ORDER BY ordinal", (run_id,)
        ).fetchall()
        action_states = {
            action["action_id"]: [
                state["status"]
                for state in self._connection.execute(
                    "SELECT status FROM action_transitions WHERE run_id = ? AND action_id = ? ORDER BY ordinal",
                    (run_id, action["action_id"]),
                ).fetchall()
            ]
            for action in actions
        }
        attempted_calls = self._connection.execute(
            """SELECT request_id, action_id, operation, component_version, timestamp
               FROM attempted_calls WHERE run_id = ? ORDER BY ordinal""",
            (run_id,),
        ).fetchall()
        return {
            "schema_version": "v1",
            "run_id": row["run_id"],
            "mission_id": row["mission_id"],
            "action_ids": [action["action_id"] for action in actions],
            "attempted_calls": [dict(call) for call in attempted_calls],
            "mission_result": row["mission_result"],
            "tool_call_valid": bool(row["tool_call_valid"]),
            "state_transitions": {
                "mission": [state["status"] for state in mission_states],
                "actions": action_states,
            },
            "timeout_detected": bool(row["timeout_detected"]),
            "reconciliation_performed": bool(row["reconciliation_performed"]),
            "retry_budget": row["retry_budget"],
            "retry_count": row["retry_count"],
            "recovery_result": row["recovery_result"],
            "hitl_escalated": bool(row["hitl_escalated"]),
            "mission_duration_ms": row["mission_duration_ms"],
            "error_category": row["error_category"],
            "component_versions": json.loads(row["component_versions_json"]),
            "started_at": row["started_at"],
            "completed_at": row["completed_at"],
        }


def write_run_artifacts(
    run: RecoveryRun,
    *,
    run_root: Path,
    run_id: str,
    started_at: str,
    completed_at: str,
) -> RunArtifacts:
    """Write the canonical run's SQLite database, JSONL trace, and JSON summary."""
    if run_root.name != run_id:
        raise PersistenceValidationError("run_root directory name must equal run_id")
    store = MissionLifecycleStore(run_root / "lifecycle.sqlite3")
    try:
        summary = store.persist_recovery_run(
            run,
            run_id=run_id,
            started_at=started_at,
            completed_at=completed_at,
        )
        events = store._connection.execute(
            "SELECT payload_json FROM events WHERE run_id = ? ORDER BY ordinal", (run_id,)
        ).fetchall()
    finally:
        store.close()
    trace_path = run_root / "trace.jsonl"
    summary_path = run_root / "summary.json"
    with trace_path.open("w", encoding="utf-8") as trace_file:
        for event in events:
            trace_file.write(event["payload_json"] + "\n")
    with summary_path.open("w", encoding="utf-8") as summary_file:
        json.dump(summary, summary_file, indent=2, sort_keys=True)
        summary_file.write("\n")
    return RunArtifacts(
        run_id=run_id,
        database_path=run_root / "lifecycle.sqlite3",
        trace_path=trace_path,
        summary_path=summary_path,
        summary=summary,
    )
