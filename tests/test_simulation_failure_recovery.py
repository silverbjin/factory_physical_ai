from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from simulation_runtime.failure_recovery import (  # noqa: E402
    MANDATORY_SCENARIO_IDS,
    load_manifest,
    run_failure_suite,
)
from scripts.run_simulation_failure_recovery import build_evidence  # noqa: E402


def test_manifest_has_stable_complete_bounded_scenarios() -> None:
    manifest = load_manifest()

    assert [scenario["id"] for scenario in manifest["scenarios"]] == list(MANDATORY_SCENARIO_IDS)
    assert all(set(("id", "layer", "backend", "injection", "expected_decision", "budget_ms")) <= set(scenario) for scenario in manifest["scenarios"])
    assert all(isinstance(scenario["budget_ms"], int) and 0 < scenario["budget_ms"] <= 5_000 for scenario in manifest["scenarios"])


def test_suite_fails_closed_reconciles_before_retry_and_cleans_up() -> None:
    suite = run_failure_suite()

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

    uncertain = next(row for row in suite["scenarios"] if row["id"] == "SIM009-VERIFY-UNCERTAIN")
    stale = next(row for row in suite["scenarios"] if row["id"] == "SIM009-VERIFY-STALE")
    assert uncertain["decision"] == "RECONCILE"
    assert stale["decision"] == "HITL"


def test_runner_evidence_is_machine_readable_and_contains_no_successful_unknown_or_uncertain() -> None:
    evidence = build_evidence()

    assert evidence["task_id"] == "TASK-SIM-009"
    assert evidence["task_specific_result"] == "SIM_FAILURE_SUITE_READY"
    assert evidence["cleanup_complete"] is True
    assert all(row["pass"] for row in evidence["scenarios"])
    assert not any(row["decision"] == "SUCCESS" for row in evidence["scenarios"] if row["outcome_kind"] in {"unknown", "uncertain", "contradictory"})
