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
    _validate_live_navigation_evidence,
    load_manifest,
    run_failure_suite,
    classify_repeatability_run,
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


def test_repeatability_classifies_bootstrap_failure_as_infrastructure_not_semantic() -> None:
    run = {
        "task_specific_result": "SIM_FAILURE_SUITE_BLOCKED",
        "scenarios": [
            {"id": "SIM009-NAV-BLOCKED", "live_runtime_ready": False, "runtime_calls": 0},
        ],
    }

    assert classify_repeatability_run(run) == "INFRASTRUCTURE_NOT_READY"


def test_blocked_budget_covers_bounded_goal_acceptance_and_terminal_waits() -> None:
    manifest = load_manifest()
    budgets = {scenario["id"]: scenario["budget_ms"] for scenario in manifest["scenarios"]}

    assert LIVE_NAVIGATION_CALL_BUDGET_MS == (
        3 * INTENTIONAL_FAULT_TIMEOUT_MS
        + LIVE_RUNTIME_SCHEDULING_MARGIN_MS
    )
    assert budgets["SIM009-NAV-BLOCKED"] == LIVE_NAVIGATION_CALL_BUDGET_MS
    assert 0 < budgets["SIM009-NAV-BLOCKED"] <= MAX_SCENARIO_BUDGET_MS
    assert budgets["SIM009-NAV-ABORTED"] == 3000
    assert budgets["SIM009-NAV-TIMEOUT-RETRY"] == LIVE_NAVIGATION_RETRY_BUDGET_MS
    assert budgets["SIM009-NAV-TF-UNAVAILABLE"] == 12000


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


@pytest.mark.parametrize(
    ("scenario_id", "destination_id"),
    [
        ("SIM009-NAV-BLOCKED", "blocked-bay"),
        ("SIM009-NAV-ABORTED", "line-b-drop"),
        ("SIM009-NAV-TF-UNAVAILABLE", "line-b-drop"),
    ],
)
def test_live_navigation_faults_route_to_distinct_declared_destinations(
    scenario_id: str, destination_id: str,
) -> None:
    request = _action_request("navigation.execute", scenario_id=scenario_id)

    assert request["destination_id"] == destination_id


def test_goal_tracker_records_one_shot_fault_and_filters_evidence_by_scenario() -> None:
    from scripts.sim009_goal_tracked_navigation import (
        GoalAttemptRecord,
        GoalTrackedGazeboNav2Runtime,
    )

    runtime = object.__new__(GoalTrackedGazeboNav2Runtime)
    runtime.goal_attempts = [
        GoalAttemptRecord(
            mission_id="11111111-1111-4111-8111-111111111111",
            action_id="22222222-2222-4222-8222-222222222222",
            idempotency_key="sim009-navigation",
            destination_id="blocked-bay",
            nav2_goal_uuid="33333333-3333-4333-8333-333333333333",
            scenario_id="SIM009-NAV-BLOCKED",
            scenario_execution_id="execution-blocked",
            injection_kind="blocked_path",
            frame_id="map",
        ),
        GoalAttemptRecord(
            mission_id="44444444-4444-4444-8444-444444444444",
            action_id="55555555-5555-4555-8555-555555555555",
            idempotency_key="sim009-navigation",
            destination_id="line-b-drop",
            nav2_goal_uuid="66666666-6666-4666-8666-666666666666",
            scenario_id="SIM009-NAV-ABORTED",
            scenario_execution_id="execution-aborted",
            injection_kind="missing_behavior_tree",
            frame_id="map",
            behavior_tree="/tmp/sim009-missing-tree.xml",
        ),
    ]
    runtime.measurements = {"cleanup": {"bounded": True}}
    runtime._tf_probe_records = []

    evidence = runtime.evidence_for("execution-aborted")

    assert [attempt["scenario_id"] for attempt in evidence["goal_attempts"]] == [
        "SIM009-NAV-ABORTED",
    ]
    attempt = evidence["goal_attempts"][0]
    assert attempt["destination_id"] == "line-b-drop"
    assert attempt["behavior_tree"] == "/tmp/sim009-missing-tree.xml"
    assert attempt["injection_kind"] == "missing_behavior_tree"


def test_goal_tracker_reads_only_the_current_attempt_log_window(tmp_path: Path) -> None:
    from scripts.sim009_goal_tracked_navigation import GoalTrackedGazeboNav2Runtime

    log_path = tmp_path / "nav2.log"
    log_path.write_text("BLOCKED_MARKER\n")
    runtime = object.__new__(GoalTrackedGazeboNav2Runtime)
    runtime.measurements = {"processes": [{"log_path": str(log_path)}]}

    aborted_window_start = runtime._capture_log_offsets()
    with log_path.open("a") as log_file:
        log_file.write("ABORTED_BT_MARKER\n")
    aborted_log, aborted_attributed, _ = runtime._read_server_log_window(aborted_window_start)

    assert aborted_attributed is True
    assert "ABORTED_BT_MARKER" in aborted_log
    assert "BLOCKED_MARKER" not in aborted_log

    tf_window_start = runtime._capture_log_offsets()
    with log_path.open("a") as log_file:
        log_file.write("TF_MISSING_FRAME_MARKER\n")
    tf_log, tf_attributed, _ = runtime._read_server_log_window(tf_window_start)

    assert tf_attributed is True
    assert "TF_MISSING_FRAME_MARKER" in tf_log
    assert "BLOCKED_MARKER" not in tf_log
    assert "ABORTED_BT_MARKER" not in tf_log


def test_goal_tracker_fails_closed_when_a_log_window_cannot_be_attributed(tmp_path: Path) -> None:
    from scripts.sim009_goal_tracked_navigation import GoalTrackedGazeboNav2Runtime

    runtime = object.__new__(GoalTrackedGazeboNav2Runtime)
    runtime.measurements = {"processes": [{"log_path": str(tmp_path / "missing.log")}]}

    log, attributed, _ = runtime._read_server_log_window({str(tmp_path / "missing.log"): 0})

    assert log == ""
    assert attributed is False


def test_goal_tracker_preflights_its_private_action_client_with_a_bounded_wait() -> None:
    from scripts.sim009_goal_tracked_navigation import GoalTrackedGazeboNav2Runtime

    class Client:
        def __init__(self) -> None:
            self.timeouts: list[float] = []

        def wait_for_server(self, *, timeout_sec: float) -> bool:
            self.timeouts.append(timeout_sec)
            return True

    client = Client()
    runtime = object.__new__(GoalTrackedGazeboNav2Runtime)
    runtime.measurements = {"readiness": []}
    runtime._client = lambda: (object(), object(), client, object())

    assert runtime._preflight_private_action_client() is True
    assert client.timeouts == [5.0]
    assert runtime.measurements["readiness"][-1] == {
        "sim009_private_action_client": True,
        "timeout_seconds": 5.0,
    }


def test_goal_tracker_evidence_counts_only_the_selected_scenario_execution() -> None:
    from scripts.sim009_goal_tracked_navigation import (
        GoalAttemptRecord,
        GoalTrackedGazeboNav2Runtime,
    )

    runtime = object.__new__(GoalTrackedGazeboNav2Runtime)
    runtime.measurements = {"cleanup": {}}
    runtime._tf_probe_records = []
    runtime.goal_attempts = []
    for execution_id, scenario_id, goal_uuid, terminal_status in (
        ("execution-blocked", "SIM009-NAV-BLOCKED", "11111111-1111-4111-8111-111111111111", "6"),
        ("execution-aborted", "SIM009-NAV-ABORTED", "22222222-2222-4222-8222-222222222222", "6"),
        ("execution-timeout", "SIM009-NAV-TIMEOUT-RETRY", "33333333-3333-4333-8333-333333333333", "5"),
        ("execution-timeout", "SIM009-NAV-TIMEOUT-RETRY", "44444444-4444-4444-8444-444444444444", "4"),
        ("execution-tf", "SIM009-NAV-TF-UNAVAILABLE", "55555555-5555-4555-8555-555555555555", "6"),
    ):
        runtime.goal_attempts.append(GoalAttemptRecord(
            mission_id="66666666-6666-4666-8666-666666666666",
            action_id="77777777-7777-4777-8777-777777777777" if execution_id == "execution-timeout" else goal_uuid,
            idempotency_key="sim009-navigation",
            destination_id="line-b-drop",
            nav2_goal_uuid=goal_uuid,
            scenario_id=scenario_id,
            scenario_execution_id=execution_id,
            terminal_status=terminal_status,
        ))

    counts = {
        execution_id: runtime.evidence_for(execution_id)
        for execution_id in ("execution-blocked", "execution-aborted", "execution-timeout", "execution-tf")
    }

    assert [counts[key]["runtime_calls"] for key in counts] == [1, 1, 2, 1]
    assert counts["execution-timeout"]["logical_side_effect_count"] == 1
    assert counts["execution-tf"]["logical_side_effect_count"] == 0


def test_faulted_goal_cannot_classify_a_native_success_as_the_injected_failure() -> None:
    from scripts.sim009_goal_tracked_navigation import (
        GoalAttemptRecord,
        GoalTrackedGazeboNav2Runtime,
    )

    class CompletedFuture:
        def result(self) -> object:
            return SimpleNamespace(status=4, result=SimpleNamespace(error_code=0, error_msg=""))

    runtime = object.__new__(GoalTrackedGazeboNav2Runtime)
    attempt = GoalAttemptRecord(
        mission_id="11111111-1111-4111-8111-111111111111",
        action_id="22222222-2222-4222-8222-222222222222",
        idempotency_key="sim009-navigation",
        destination_id="line-b-drop",
        nav2_goal_uuid="33333333-3333-4333-8333-333333333333",
        scenario_id="SIM009-NAV-ABORTED",
        injection_kind="missing_behavior_tree",
        behavior_tree="/tmp/sim009-missing-behavior-tree.xml",
        result_future=CompletedFuture(),
    )

    observation = runtime._observation_from_result(attempt)

    assert observation.observed_status == "failed"
    assert observation.error_code == "SIM009_FAULT_NOT_OBSERVED"


def test_unarmed_blocked_attempt_is_bound_to_its_scenario_execution() -> None:
    from scripts.sim009_goal_tracked_navigation import (
        GoalAttemptRecord,
        GoalTrackedGazeboNav2Runtime,
    )

    runtime = object.__new__(GoalTrackedGazeboNav2Runtime)
    runtime.goal_attempts = []
    runtime._attempts_by_action_id = {}
    runtime._tf_probe_records = []
    runtime.measurements = {"cleanup": {}}
    context = runtime.begin_scenario("SIM009-NAV-BLOCKED")
    runtime._record_attempt(GoalAttemptRecord(
        mission_id="11111111-1111-4111-8111-111111111111",
        action_id="22222222-2222-4222-8222-222222222222",
        idempotency_key="sim009-navigation",
        destination_id="blocked-bay",
        nav2_goal_uuid="33333333-3333-4333-8333-333333333333",
    ))
    runtime.end_scenario(context)

    evidence = runtime.evidence_for(context.scenario_execution_id)

    assert evidence["scenario_id"] == "SIM009-NAV-BLOCKED"
    assert evidence["scenario_execution_id"] == context.scenario_execution_id
    assert [item["nav2_goal_uuid"] for item in evidence["goal_attempts"]] == [
        "33333333-3333-4333-8333-333333333333",
    ]
    assert evidence["goal_attempts"][0]["injection_kind"] == "none"


def test_tf_probe_evidence_is_filtered_by_scenario_execution_id() -> None:
    from scripts.sim009_goal_tracked_navigation import GoalTrackedGazeboNav2Runtime

    runtime = object.__new__(GoalTrackedGazeboNav2Runtime)
    runtime.goal_attempts = []
    runtime._attempts_by_action_id = {}
    runtime._tf_probe_records = []
    runtime.measurements = {"cleanup": {}}
    blocked = runtime.begin_scenario("SIM009-NAV-BLOCKED")
    runtime._record_tf_probe("sim009_tf_baseline", "map", "base_link", True)
    runtime.end_scenario(blocked)
    tf_fault = runtime.begin_scenario("SIM009-NAV-TF-UNAVAILABLE")
    runtime._record_tf_probe("sim009_tf_baseline", "map", "base_link", True)
    runtime._record_tf_probe("sim009_tf_injected_missing", "sim009_missing_tf_frame", "base_link", False)
    runtime.end_scenario(tf_fault)

    assert [item["label"] for item in runtime.evidence_for(blocked.scenario_execution_id)["tf_probes"]] == [
        "sim009_tf_baseline",
    ]
    assert [item["label"] for item in runtime.evidence_for(tf_fault.scenario_execution_id)["tf_probes"]] == [
        "sim009_tf_baseline", "sim009_tf_injected_missing",
    ]


def test_tf_fault_rejects_unavailable_baseline_even_with_local_aborted_goal() -> None:
    request = _action_request("navigation.execute", scenario_id="SIM009-NAV-TF-UNAVAILABLE")
    evidence = {
        "scenario_id": "SIM009-NAV-TF-UNAVAILABLE",
        "scenario_execution_id": "execution-tf",
        "goal_attempts": [{
            "scenario_id": "SIM009-NAV-TF-UNAVAILABLE",
            "scenario_execution_id": "execution-tf",
            "action_id": request["action_id"],
            "destination_id": "line-b-drop",
            "nav2_goal_uuid": "goal-tf",
            "terminal_goal_uuid": "goal-tf",
            "terminal_status": "6",
            "frame_id": "sim009_missing_tf_frame",
            "behavior_tree": "",
            "injection_kind": "missing_goal_frame",
            "native_error_code": "202",
            "native_error_message": "TF unavailable",
            "server_log_attributed": True,
        }],
        "tf_probes": [
            {"label": "sim009_tf_baseline", "available": False},
            {"label": "sim009_tf_injected_missing", "available": False},
        ],
    }

    assert not _validate_live_navigation_evidence(
        "SIM009-NAV-TF-UNAVAILABLE", request, evidence,
    )


def test_navigation_fault_validator_rejects_reused_or_generic_aborted_evidence() -> None:
    request = _action_request("navigation.execute", scenario_id="SIM009-NAV-ABORTED")
    reused_blocked = {
        "scenario_id": "SIM009-NAV-BLOCKED",
        "scenario_execution_id": "execution-blocked",
        "goal_attempts": [{
            "scenario_id": "SIM009-NAV-BLOCKED",
            "scenario_execution_id": "execution-blocked",
            "action_id": request["action_id"],
            "destination_id": "blocked-bay",
            "nav2_goal_uuid": "goal-blocked",
            "terminal_goal_uuid": "goal-blocked",
            "terminal_status": "6",
            "frame_id": "map",
            "behavior_tree": "",
            "injection_kind": "none",
            "native_error_code": "204",
            "native_error_message": "goal outside map",
        }],
        "tf_probes": [],
    }
    generic_abort = {
        "scenario_id": "SIM009-NAV-ABORTED",
        "scenario_execution_id": "execution-aborted",
        "goal_attempts": [{
            "scenario_id": "SIM009-NAV-ABORTED",
            "scenario_execution_id": "execution-aborted",
            "action_id": request["action_id"],
            "destination_id": "line-b-drop",
            "nav2_goal_uuid": "goal-aborted",
            "terminal_goal_uuid": "goal-aborted",
            "terminal_status": "6",
            "frame_id": "map",
            "behavior_tree": "/tmp/sim009-missing-behavior-tree.xml",
            "injection_kind": "missing_behavior_tree",
            "native_error_code": "0",
            "native_error_message": None,
            "server_log_tail": "",
        }],
        "tf_probes": [],
    }

    assert not _validate_live_navigation_evidence("SIM009-NAV-ABORTED", request, reused_blocked)
    assert not _validate_live_navigation_evidence("SIM009-NAV-ABORTED", request, generic_abort)


def test_tf_fault_requires_complete_local_live_proof() -> None:
    request = _action_request("navigation.execute", scenario_id="SIM009-NAV-TF-UNAVAILABLE")
    evidence = {
        "scenario_id": "SIM009-NAV-TF-UNAVAILABLE",
        "scenario_execution_id": "execution-tf",
        "goal_attempts": [{
            "scenario_id": "SIM009-NAV-TF-UNAVAILABLE",
            "scenario_execution_id": "execution-tf",
            "action_id": request["action_id"],
            "destination_id": "line-b-drop",
            "nav2_goal_uuid": "goal-tf",
            "terminal_goal_uuid": "goal-tf",
            "terminal_status": "6",
            "frame_id": "sim009_missing_tf_frame",
            "behavior_tree": "",
            "injection_kind": "missing_goal_frame",
            "native_error_code": "202",
            "native_error_message": "TF unavailable",
            "server_log_attributed": True,
        }],
        "tf_probes": [
            {"scenario_execution_id": "execution-tf", "label": "sim009_tf_baseline", "available": True},
            {"scenario_execution_id": "execution-tf", "label": "sim009_tf_injected_missing", "available": False},
        ],
    }

    assert _validate_live_navigation_evidence("SIM009-NAV-TF-UNAVAILABLE", request, evidence)


def test_blocked_fault_rejects_aborted_fault_evidence() -> None:
    request = _action_request("navigation.execute", scenario_id="SIM009-NAV-BLOCKED")
    evidence = {
        "scenario_id": "SIM009-NAV-ABORTED",
        "scenario_execution_id": "execution-aborted",
        "goal_attempts": [{
            "scenario_id": "SIM009-NAV-ABORTED",
            "scenario_execution_id": "execution-aborted",
            "action_id": request["action_id"],
            "destination_id": "line-b-drop",
            "nav2_goal_uuid": "goal-aborted",
            "terminal_goal_uuid": "goal-aborted",
            "terminal_status": "6",
            "frame_id": "map",
            "behavior_tree": "/tmp/sim009-missing-behavior-tree.xml",
            "injection_kind": "missing_behavior_tree",
            "native_error_code": "0",
            "native_error_message": None,
        }],
        "tf_probes": [],
    }

    assert not _validate_live_navigation_evidence("SIM009-NAV-BLOCKED", request, evidence)


def test_timeout_retry_attempts_share_only_its_scenario_execution() -> None:
    from scripts.sim009_goal_tracked_navigation import (
        GoalAttemptRecord,
        GoalTrackedGazeboNav2Runtime,
    )

    runtime = object.__new__(GoalTrackedGazeboNav2Runtime)
    runtime.goal_attempts = []
    runtime._attempts_by_action_id = {}
    runtime._tf_probe_records = []
    runtime.measurements = {"cleanup": {}}
    timeout = runtime.begin_scenario("SIM009-NAV-TIMEOUT-RETRY")
    for goal_uuid in ("33333333-3333-4333-8333-333333333333", "44444444-4444-4444-8444-444444444444"):
        runtime._record_attempt(GoalAttemptRecord(
            mission_id="11111111-1111-4111-8111-111111111111",
            action_id="22222222-2222-4222-8222-222222222222",
            idempotency_key="sim009-navigation",
            destination_id="line-b-drop",
            nav2_goal_uuid=goal_uuid,
        ))
    runtime.end_scenario(timeout)
    unrelated = runtime.begin_scenario("SIM009-NAV-BLOCKED")
    runtime._record_attempt(GoalAttemptRecord(
        mission_id="55555555-5555-4555-8555-555555555555",
        action_id="66666666-6666-4666-8666-666666666666",
        idempotency_key="sim009-navigation",
        destination_id="blocked-bay",
        nav2_goal_uuid="77777777-7777-4777-8777-777777777777",
    ))
    runtime.end_scenario(unrelated)

    evidence = runtime.evidence_for(timeout.scenario_execution_id)

    assert {item["nav2_goal_uuid"] for item in evidence["goal_attempts"]} == {
        "33333333-3333-4333-8333-333333333333",
        "44444444-4444-4444-8444-444444444444",
    }


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
    context = runtime.begin_scenario("SIM009-NAV-TIMEOUT-RETRY")
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
    runtime.end_scenario(context)

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
