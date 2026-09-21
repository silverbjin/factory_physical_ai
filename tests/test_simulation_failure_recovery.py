from __future__ import annotations

import hashlib
import json
import sys
from types import SimpleNamespace
from pathlib import Path
from datetime import datetime

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from simulation_runtime.failure_recovery import (  # noqa: E402
    INTENTIONAL_FAULT_TIMEOUT_MS,
    LIVE_NAVIGATION_CALL_BUDGET_MS,
    LIVE_NAVIGATION_RETRY_BUDGET_MS,
    LIVE_RUNTIME_SCHEDULING_MARGIN_MS,
    MAX_SCENARIO_BUDGET_MS,
    MANDATORY_SCENARIO_IDS,
    NORMAL_RECOVERY_TIMEOUT_MS,
    _ScriptedNavigationRuntime,
    _action_request,
    _authorized_retry,
    _mission_verification_route,
    load_manifest,
    run_failure_suite,
)
from simulation_runtime.navigation_backend import RuntimeObservation  # noqa: E402
from scripts.run_simulation_failure_recovery import build_evidence  # noqa: E402


def test_manifest_has_stable_complete_bounded_scenarios() -> None:
    manifest = load_manifest()

    assert [scenario["id"] for scenario in manifest["scenarios"]] == list(MANDATORY_SCENARIO_IDS)
    assert all(set(("id", "layer", "backend", "injection", "expected_decision", "budget_ms")) <= set(scenario) for scenario in manifest["scenarios"])
    assert all(isinstance(scenario["budget_ms"], int) and 0 < scenario["budget_ms"] <= MAX_SCENARIO_BUDGET_MS for scenario in manifest["scenarios"])

    budgets = {scenario["id"]: scenario["budget_ms"] for scenario in manifest["scenarios"]}
    assert budgets["SIM009-NAV-BLOCKED"] == LIVE_NAVIGATION_CALL_BUDGET_MS
    assert budgets["SIM009-NAV-TIMEOUT-RETRY"] == LIVE_NAVIGATION_RETRY_BUDGET_MS
    assert LIVE_NAVIGATION_RETRY_BUDGET_MS == (
        INTENTIONAL_FAULT_TIMEOUT_MS
        + NORMAL_RECOVERY_TIMEOUT_MS
        + LIVE_RUNTIME_SCHEDULING_MARGIN_MS
    )


def test_suite_fails_closed_reconciles_before_retry_and_cleans_up() -> None:
    suite = run_failure_suite(navigation_runtime_factory=_ScriptedNavigationRuntime)

    assert suite["task_specific_result"] == "SIM_FAILURE_SUITE_READY"
    assert [row["id"] for row in suite["scenarios"]] == list(MANDATORY_SCENARIO_IDS)
    assert all(row["pass"] and row["cleanup_complete"] for row in suite["scenarios"])

    nav_timeout = next(row for row in suite["scenarios"] if row["id"] == "SIM009-NAV-TIMEOUT-RETRY")
    assert nav_timeout["decision"] == "RETRY"
    assert nav_timeout["reconciliation"]["observed_status"] == "failed"
    assert nav_timeout["identity"]["action_id_stable"] is True
    assert nav_timeout["identity"]["idempotency_key_stable"] is True
    assert nav_timeout["identity"]["retry_request_id_new"] is True
    assert nav_timeout["identity"]["attempt_incremented"] is True
    assert nav_timeout["retry_authorization"]["reconciliation_completed"] is True
    assert nav_timeout["retry_authorization"]["resolved_status"] == "failed"
    assert nav_timeout["retry_authorization"]["error"]["retryable"] is True
    assert nav_timeout["retry_request"]["retry_budget_remaining"] == 0
    assert nav_timeout["logical_side_effect_count"] == 1
    assert nav_timeout["cleanup_complete"] is True

    uncertain = next(row for row in suite["scenarios"] if row["id"] == "SIM009-VERIFY-UNCERTAIN")
    stale = next(row for row in suite["scenarios"] if row["id"] == "SIM009-VERIFY-STALE")
    assert uncertain["decision"] == "RECONCILE"
    assert stale["decision"] == "HITL"
    mismatch = next(row for row in suite["scenarios"] if row["id"] == "SIM009-VERIFY-MISMATCH")
    assert mismatch["mission"]["mission_state"] == "recovering"
    assert mismatch["mission"]["mission_success_committed"] is False
    assert uncertain["mission"]["mission_state"] == "reconciling"
    assert stale["mission"]["mission_state"] == "escalated"


def test_runner_evidence_is_machine_readable_and_contains_no_successful_unknown_or_uncertain() -> None:
    evidence = build_evidence(navigation_runtime_factory=_ScriptedNavigationRuntime)

    assert evidence["task_id"] == "TASK-SIM-009"
    assert evidence["task_specific_result"] == "SIM_FAILURE_SUITE_READY"
    assert evidence["cleanup_complete"] is True
    assert set(evidence["accepted_bindings"]) == {"SIM-004", "SIM-005", "SIM-006", "SIM-008"}
    assert evidence["simulation_authority"] == {"navigation_system_world": "gazebo_harmonic", "manipulation_fault_bench": "mujoco", "live_dual_world": False, "physical_dependency": False, "navigation_runtime": "test_fixture"}
    assert all(row["pass"] for row in evidence["scenarios"])
    assert not any(row["decision"] == "SUCCESS" for row in evidence["scenarios"] if row["outcome_kind"] in {"unknown", "uncertain", "contradictory"})


def test_accepted_binding_rejects_evidence_that_does_not_match_its_accepted_hash(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    import simulation_runtime.failure_recovery as failure_recovery

    evidence_path = tmp_path / "results/simulation/SIM-004_navigation_backend.json"
    evidence_path.parent.mkdir(parents=True)
    evidence_path.write_text(json.dumps({"task_specific_result": "SIM_NAVIGATION_BACKEND_READY"}))
    acceptance_path = tmp_path / "results/reviews/SIM-004_acceptance.json"
    acceptance_path.parent.mkdir(parents=True)
    acceptance_path.write_text(json.dumps({
        "status": "ACCEPT",
        "evidence": {
            "path": "results/simulation/SIM-004_navigation_backend.json",
            "sha256": "0" * 64,
        },
    }))
    monkeypatch.setattr(failure_recovery, "ROOT", tmp_path)

    with pytest.raises(ValueError, match="hash"):
        failure_recovery._accepted_binding("SIM-004")


def test_verification_recovery_uses_the_accepted_mission_transition_path() -> None:
    route = _mission_verification_route("RECOVERY", {"verdict": "fail"})

    assert route["mission_state"] == "recovering"
    assert route["transition_path"] == ["executing", "reconciling", "recovering"]
    assert route["mission_success_committed"] is False


@pytest.mark.parametrize(
    ("resolved_status", "retryable", "expected_authorization"),
    [
        ("succeeded", True, False),
        ("failed", True, True),
        ("unknown", True, False),
        ("failed", False, False),
    ],
    ids=(
        "reconciled-success-suppresses-retry",
        "retryable-failure-authorizes-retry",
        "reconciled-unknown-prohibits-retry",
        "non-retryable-failure-prohibits-retry",
    ),
)
def test_retry_authorization_requires_authoritative_retryable_failure(
    resolved_status: str, retryable: bool, expected_authorization: bool,
) -> None:
    previous = _action_request("navigation.execute")
    resolved = RuntimeObservation(
        resolved_status,
        error_code="NAV_RESULT",
        error_message="authoritative reconciliation result",
        error_category="EXECUTION_FAILED",
        retryable=retryable,
    )

    authorized = _authorized_retry(
        previous,
        reconciliation={"result": "success", "observed_status": resolved_status},
        resolved=resolved,
    )

    assert (authorized is not None) is expected_authorization
    if expected_authorization:
        retry, authorization = authorized
        assert authorization["resolved_status"] == "failed"
        assert authorization["error"]["retryable"] is True
        assert retry["attempt"] == previous["attempt"] + 1


def test_timeout_fault_and_recovery_retry_use_distinct_request_deadlines() -> None:
    first = _action_request(
        "navigation.execute", timeout_ms=INTENTIONAL_FAULT_TIMEOUT_MS,
    )
    first["destination_id"] = "line-b-drop"
    authorized = _authorized_retry(
        first,
        reconciliation={"result": "success", "observed_status": "failed"},
        resolved=RuntimeObservation("failed", retryable=True),
    )

    assert authorized is not None
    retry, _ = authorized
    assert first["timeout_ms"] == INTENTIONAL_FAULT_TIMEOUT_MS
    assert retry["timeout_ms"] == NORMAL_RECOVERY_TIMEOUT_MS
    assert first["timeout_ms"] != retry["timeout_ms"]
    retry_timestamp = datetime.fromisoformat(retry["timestamp"].replace("Z", "+00:00"))
    retry_deadline = datetime.fromisoformat(retry["deadline_at"].replace("Z", "+00:00"))
    assert (retry_deadline - retry_timestamp).total_seconds() * 1000 == NORMAL_RECOVERY_TIMEOUT_MS


def test_goal_attempt_record_binds_one_nav2_goal_to_its_terminal_result() -> None:
    from scripts.sim009_goal_tracked_navigation import GoalAttemptRecord

    attempt = GoalAttemptRecord(
        mission_id="11111111-1111-4111-8111-111111111111",
        action_id="22222222-2222-4222-8222-222222222222",
        idempotency_key="sim009-navigation",
        destination_id="line-b-drop",
        nav2_goal_uuid="33333333-3333-4333-8333-333333333333",
    )

    assert attempt.terminal_goal_uuid == "33333333-3333-4333-8333-333333333333"
    assert attempt.terminal_status is None


def test_goal_tracker_retains_each_nav2_goal_for_one_logical_effect() -> None:
    from scripts.sim009_goal_tracked_navigation import (
        GoalAttemptRecord,
        GoalTrackedGazeboNav2Runtime,
    )

    runtime = object.__new__(GoalTrackedGazeboNav2Runtime)
    runtime.goal_attempts = []
    runtime._attempts_by_action_id = {}
    first = GoalAttemptRecord(
        mission_id="11111111-1111-4111-8111-111111111111",
        action_id="22222222-2222-4222-8222-222222222222",
        idempotency_key="sim009-navigation",
        destination_id="line-b-drop",
        nav2_goal_uuid="33333333-3333-4333-8333-333333333333",
    )
    retry = GoalAttemptRecord(
        mission_id=first.mission_id,
        action_id=first.action_id,
        idempotency_key=first.idempotency_key,
        destination_id=first.destination_id,
        nav2_goal_uuid="44444444-4444-4444-8444-444444444444",
    )

    runtime._record_attempt(first)
    runtime._record_attempt(retry)

    assert [attempt.nav2_goal_uuid for attempt in runtime.goal_attempts] == [
        first.nav2_goal_uuid,
        retry.nav2_goal_uuid,
    ]
    assert runtime._attempts_by_action_id[first.action_id] == retry


def test_timeout_reconciliation_cancels_the_same_goal_before_retry() -> None:
    from scripts.sim009_goal_tracked_navigation import (
        GoalAttemptRecord,
        GoalTrackedGazeboNav2Runtime,
    )

    class Future:
        def __init__(self, *, done: bool, result: object | None = None) -> None:
            self.done_value = done
            self.value = result

        def done(self) -> bool:
            return self.done_value

        def result(self) -> object:
            return self.value

    class GoalHandle:
        def __init__(self, cancellation: Future) -> None:
            self.cancellation = cancellation
            self.cancel_calls = 0

        def cancel_goal_async(self) -> Future:
            self.cancel_calls += 1
            return self.cancellation

    class Spinner:
        def __init__(self, terminal: Future) -> None:
            self.terminal = terminal

        def spin_until_future_complete(self, _node: object, _future: Future, timeout_sec: float) -> None:
            assert timeout_sec > 0
            self.terminal.done_value = True

    terminal = Future(done=False, result=SimpleNamespace(status=5))
    handle = GoalHandle(Future(done=True))
    attempt = GoalAttemptRecord(
        mission_id="11111111-1111-4111-8111-111111111111",
        action_id="22222222-2222-4222-8222-222222222222",
        idempotency_key="sim009-navigation",
        destination_id="line-b-drop",
        nav2_goal_uuid="33333333-3333-4333-8333-333333333333",
        goal_handle=handle,
        result_future=terminal,
    )
    runtime = object.__new__(GoalTrackedGazeboNav2Runtime)
    runtime._rclpy = Spinner(terminal)
    runtime._node = object()

    observation = runtime._reconcile_timeout_attempt(attempt)

    assert handle.cancel_calls == 1
    assert attempt.terminal_goal_uuid == attempt.nav2_goal_uuid
    assert attempt.terminal_status == "5"
    assert observation.observed_status == "failed"
    assert observation.retryable is True
