#!/usr/bin/env python3
"""Read-only, fail-closed verifier for the Simulation E2E qualification gate."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

TASKS = {
    "SIM-003": "SIM_BASELINE_READY", "SIM-004": "SIM_NAVIGATION_BACKEND_READY",
    "SIM-005": "SIM_MANIPULATION_BACKEND_READY", "SIM-006": "SIM_VERIFICATION_BACKEND_READY",
    "SIM-007": "SIM_MISSION_INTEGRATION_READY", "SIM-008": "SIM_NORMAL_E2E_READY",
    "SIM-009": "SIM_FAILURE_SUITE_READY", "SIM-010": "SIM_OBSERVABILITY_REGRESSION_READY",
}
def _rows(data: dict[str, Any], key: str) -> list[dict[str, Any]]:
    value = data.get(key)
    return value if isinstance(value, list) and all(isinstance(row, dict) for row in value) else []

def _scenario_set(data: dict[str, Any], required: set[str], *, field: str = "id") -> bool:
    rows = _rows(data, "scenarios")
    by_id = {row.get(field): row for row in rows}
    return len(by_id) == len(rows) and required <= set(by_id) and all(by_id[name].get("pass") is True for name in required)


SIM009_SCENARIO_CONTRACTS = {
    "SIM009-L0-MALFORMED": ("L0", "malformed", "FAIL_CLOSED", "INVALID_NAVIGATION_REQUEST"),
    "SIM009-L0-UNAVAILABLE": ("L0", "unavailable", "FAIL_CLOSED", "NAVIGATION_UNAVAILABLE"),
    "SIM009-L0-CONTRADICTORY": ("L0", "contradictory", "FAIL_CLOSED", None),
    "SIM009-NAV-BLOCKED": ("L1-NAV", "failure", "FAIL_CLOSED", "NAVIGATION_ABORTED"),
    "SIM009-NAV-ABORTED": ("L1-NAV", "failure", "FAIL_CLOSED", "NAVIGATION_ABORTED"),
    "SIM009-NAV-TIMEOUT-RETRY": ("L1-NAV", "unknown", "RETRY", None),
    "SIM009-NAV-TF-UNAVAILABLE": ("L1-NAV", "failure", "FAIL_CLOSED", "NAVIGATION_TF_UNAVAILABLE"),
    "SIM009-VLA-GRASP-MISS": ("L1-VLA", "failure", "FAIL_CLOSED", "GRASP_MISS"),
    "SIM009-VLA-CONTACT-LOSS": ("L1-VLA", "failure", "FAIL_CLOSED", "CONTACT_LOSS"),
    "SIM009-VLA-WORKSPACE-LIMIT": ("L1-VLA", "failure", "FAIL_CLOSED", "WORKSPACE_LIMIT"),
    "SIM009-VLA-TIMEOUT": ("L1-VLA", "unknown", "RECONCILE", "MUJOCO_TIMEOUT"),
    "SIM009-VLA-AMBIGUOUS": ("L1-VLA", "uncertain", "FAIL_CLOSED", "INVALID_OBSERVATION"),
    "SIM009-VLA-UNKNOWN": ("L1-VLA", "unknown", "RECONCILE", "MUJOCO_OUTCOME_UNKNOWN"),
    "SIM009-VERIFY-MISMATCH": ("L2", "failure", "RECOVERY", None),
    "SIM009-VERIFY-STALE": ("L2", "failure", "HITL", None),
    "SIM009-VERIFY-UNCERTAIN": ("L2", "uncertain", "RECONCILE", None),
}


def _result_has_error(row: dict[str, Any], code: str, operation: str) -> bool:
    result = row.get("result")
    return (
        isinstance(result, dict)
        and result.get("operation") == operation
        and result.get("result") == "failure"
        and result.get("status") == "failed"
        and isinstance(result.get("error"), dict)
        and result["error"].get("code") == code
    )


def _same_identity(left: dict[str, Any], right: dict[str, Any]) -> bool:
    return all(isinstance(left.get(key), str) and left.get(key) == right.get(key) for key in ("action_id", "mission_id"))


def _reconciliation(row: dict[str, Any], result: dict[str, Any], observed_status: str) -> bool:
    reconciliation = row.get("reconciliation")
    return (
        isinstance(reconciliation, dict)
        and _same_identity(result, reconciliation)
        and reconciliation.get("operation") == "action_status.get"
        and reconciliation.get("result") == "success"
        and reconciliation.get("status") == "succeeded"
        and reconciliation.get("observed_status") == observed_status
    )


def _sim009_semantics(row: dict[str, Any]) -> bool:
    scenario_id = row.get("id")
    contract = SIM009_SCENARIO_CONTRACTS.get(scenario_id)
    if contract is None:
        return False
    layer, outcome_kind, decision, error_code = contract
    if not (
        row.get("layer") == layer
        and row.get("outcome_kind") == outcome_kind
        and row.get("expected_decision") == decision
        and row.get("decision") == decision
        and row.get("pass") is True
        and row.get("within_budget") is True
        and row.get("cleanup_complete") is True
    ):
        return False
    if scenario_id == "SIM009-L0-CONTRADICTORY":
        return isinstance(row.get("validation_error"), str) and bool(row["validation_error"].strip())
    if scenario_id == "SIM009-NAV-TIMEOUT-RETRY":
        first = row.get("first_result")
        retry = row.get("retry_authorization")
        identity = row.get("identity")
        retry_result = row.get("retry_result")
        return (
            isinstance(first, dict)
            and first.get("result") == "pending" and first.get("status") == "unknown"
            and isinstance(first.get("error"), dict) and first["error"].get("code") == "NAVIGATION_TIMEOUT" and first["error"].get("retryable") is True
            and _reconciliation(row, first, "failed")
            and isinstance(retry, dict) and _same_identity(first, retry)
            and retry.get("reconciliation_completed") is True and retry.get("resolved_status") == "failed"
            and retry.get("next_attempt") == 2 and isinstance(retry.get("error"), dict) and retry["error"].get("code") == "NAVIGATION_ABORTED" and retry["error"].get("retryable") is True
            and isinstance(identity, dict) and all(identity.get(key) is True for key in ("action_id_stable", "mission_id_stable", "idempotency_key_stable", "attempt_incremented", "retry_request_id_new"))
            and isinstance(retry_result, dict) and _same_identity(first, retry_result) and retry_result.get("result") == "success" and retry_result.get("status") == "succeeded"
            and row.get("logical_side_effect_count") == 1
        )
    if scenario_id in {"SIM009-VLA-TIMEOUT", "SIM009-VLA-UNKNOWN"}:
        result = row.get("result")
        return (
            isinstance(result, dict)
            and result.get("operation") == "vla.execute" and result.get("result") == "pending" and result.get("status") == "unknown"
            and isinstance(result.get("error"), dict) and result["error"].get("code") == error_code and result["error"].get("retryable") is True
            and _reconciliation(row, result, "unknown" if scenario_id == "SIM009-VLA-TIMEOUT" else "succeeded")
        )
    if scenario_id.startswith("SIM009-VERIFY-"):
        mission = row.get("mission")
        verification = row.get("verification")
        expected = {
            "SIM009-VERIFY-MISMATCH": ("recovering", "in_progress", "fail", ["executing", "reconciling", "recovering"]),
            "SIM009-VERIFY-STALE": ("escalated", "requires_human", None, ["executing", "escalated"]),
            "SIM009-VERIFY-UNCERTAIN": ("reconciling", "in_progress", "uncertain", ["executing", "reconciling"]),
        }[scenario_id]
        if not (row.get("route") == decision and isinstance(mission, dict) and mission.get("mission_success_committed") is False and isinstance(verification, dict) and mission.get("mission_state") == expected[0] and mission.get("mission_outcome") == expected[1] and mission.get("verification_verdict") == expected[2] and mission.get("transition_path") == expected[3] and mission.get("transition") == {"from": "executing", "to": expected[0]}):
            return False
        if scenario_id == "SIM009-VERIFY-MISMATCH":
            return row.get("skill_reported_success") is True and verification.get("operation") == "verification.verify" and verification.get("result") == "success" and verification.get("status") == "succeeded" and verification.get("verdict") == "fail" and verification.get("mismatch_code") == "EXPECTED_STATE_MISMATCH"
        if scenario_id == "SIM009-VERIFY-STALE":
            return verification.get("operation") == "verification.verify" and verification.get("result") == "failure" and verification.get("status") == "failed" and isinstance(verification.get("error"), dict) and verification["error"].get("code") == "INVALID_VERIFICATION_EVIDENCE"
        return verification.get("operation") == "verification.verify" and verification.get("result") == "success" and verification.get("status") == "succeeded" and verification.get("verdict") == "uncertain" and verification.get("mismatch_code") == "INSUFFICIENT_OR_AMBIGUOUS_EVIDENCE"
    return _result_has_error(row, error_code, "vla.execute" if layer == "L1-VLA" else "navigation.execute")


def _sim009_scenarios_valid(data: dict[str, Any], required: set[str]) -> bool:
    rows = _rows(data, "scenarios")
    by_id = {row.get("id"): row for row in rows}
    return len(by_id) == len(rows) and required <= set(by_id) and all(_sim009_semantics(by_id[name]) for name in required)

def _proof(data: dict[str, Any], key: str, value: Any) -> bool:
    return isinstance(data.get("proof"), dict) and data["proof"].get(key) == value

def _state_safety(data: dict[str, Any]) -> bool:
    rows = [row for row in _rows(data, "scenarios") if row.get("layer") == "L2"]
    return bool(rows) and all(
        isinstance(row.get("mission"), dict)
        and row["mission"].get("mission_success_committed") is False
        for row in rows
    )

PREDICATES = {
    "sim_baseline_bound": ("SIM-003", lambda d: d.get("baseline_id") == "SIM_BASELINE_V1" and d.get("implementation_complete") is True),
    "accepted_contract_regression": ("SIM-003", lambda d: isinstance(d.get("deterministic_regression"), dict) and d["deterministic_regression"].get("status") == "PASS" and d["deterministic_regression"].get("probe", {}).get("returncode") == 0),
    "L0_contract_runtime": ("SIM-005", lambda d: d.get("l0_regression") == "PASS" and d.get("cleanup", {}).get("bounded") is True and d.get("cleanup", {}).get("child_processes") == 0),
    "timeout_reconciliation": ("SIM-004", lambda d: any(row.get("id") == "timeout_reconciliation" and row.get("pass") is True and row.get("status", {}).get("operation") == "action_status.get" and row["status"].get("observed_status") == "unknown" for row in _rows(d, "scenarios"))),
    "ros2_jazzy_gazebo_navigation": ("SIM-004", lambda d: d.get("runtime_identity", {}).get("gazebo", {}).get("returncode") == 0 and "/jazzy/" in d.get("runtime_identity", {}).get("ros2", {}).get("command", [""])[0] and _scenario_set(d, {"success", "invalid_goal", "unavailable", "blocked"})),
    "normal_system_e2e": ("SIM-008", lambda d: d.get("execution", {}).get("mission", {}).get("result") == "success" and d.get("execution", {}).get("mission", {}).get("status") == "completed" and d.get("execution", {}).get("lifecycle", {}).get("cleanup_complete") is True and {row.get("name") for row in d.get("execution", {}).get("steps", [])} >= {"source_navigation", "source_verification", "destination_navigation", "vla.execute", "final_verification"}),
    "required_navigation_system_failures": ("SIM-009", lambda d: _sim009_scenarios_valid(d, {"SIM009-NAV-BLOCKED", "SIM009-NAV-ABORTED", "SIM009-NAV-TIMEOUT-RETRY", "SIM009-NAV-TF-UNAVAILABLE"})),
    "manipulation_backend": ("SIM-005", lambda d: d.get("provenance", {}).get("backend_id") == "sim005-mujoco-vla-backend-v1" and d.get("provenance", {}).get("physical_target") is False),
    "required_manipulation_failures": ("SIM-005", lambda d: _scenario_set(d, {"mujoco-grasp-miss", "mujoco-contact-loss", "mujoco-workspace-limit", "mujoco-invalid-observation"}, field="scenario")),
    "model_config_provenance": ("SIM-005", lambda d: isinstance(d.get("provenance", {}).get("assets"), list) and len(d["provenance"]["assets"]) >= 3 and all(isinstance(row.get("path"), str) and isinstance(row.get("sha256"), str) and len(row["sha256"]) == 64 for row in d["provenance"]["assets"])),
    "cross_simulator_verification": ("SIM-006", lambda d: set(d.get("normalized_sources", [])) >= {"gazebo", "mujoco"} and _proof(d, "cross_backend_equivalence", "equivalent incomplete Gazebo and MuJoCo evidence produces uncertain")),
    "uncertain_never_auto_success": ("SIM-006", lambda d: _proof(d, "uncertain_confidence_promotion", "forbidden") and _proof(d, "insufficient_or_ambiguous", "uncertain")),
    "required_failure_cases": ("SIM-009", lambda d: _sim009_scenarios_valid(d, {"SIM009-L0-MALFORMED", "SIM009-L0-UNAVAILABLE", "SIM009-L0-CONTRADICTORY", "SIM009-VLA-GRASP-MISS", "SIM009-VLA-CONTACT-LOSS", "SIM009-VLA-WORKSPACE-LIMIT", "SIM009-VLA-TIMEOUT", "SIM009-VLA-AMBIGUOUS", "SIM009-VLA-UNKNOWN", "SIM009-VERIFY-MISMATCH", "SIM009-VERIFY-STALE", "SIM009-VERIFY-UNCERTAIN"})),
    "forbidden_state_transition": ("SIM-009", _state_safety),
    "leaked_process": ("SIM-009", lambda d: d.get("cleanup_complete") is True and all(row.get("cleanup_complete") is True and row.get("within_budget") is True for row in _rows(d, "scenarios"))),
    "evidence_reproducible": ("SIM-010", lambda d: d.get("deterministic_replay", {}).get("status") == "PASS" and d["deterministic_replay"].get("failures") == []),
    "regression_green": ("SIM-010", lambda d: d.get("full_repository_regression", {}).get("gate_result") == "PASS"),
    "observability_sufficient": ("SIM-010", lambda d: d.get("normal_failure_suite_coverage", {}).get("status") == "PASS" and d.get("physics_semantic_regression", {}).get("status") == "PASS"),
    "physical_dependency": ("SIM-009", lambda d: d.get("simulation_authority", {}).get("physical_dependency") is False),
    "dual_world_cosimulation_required": ("SIM-007", lambda d: d.get("system_authority", {}).get("integrated_world") == "gazebo_harmonic" and d["system_authority"].get("dual_world") is False and d["system_authority"].get("mujoco_live_world") is False),
}

def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))

def accepted(acceptance: dict[str, Any]) -> bool:
    return acceptance.get("status") == "ACCEPT" or acceptance.get("review_decision") == "ACCEPT"

def evidence_result(evidence: dict[str, Any]) -> Any:
    return evidence.get("task_specific_result", evidence.get("result"))

def evaluate(root: Path) -> dict[str, Any]:
    """Evaluate inputs only; never writes predecessor acceptance or Evidence."""
    root = Path(root)
    index_path = root / "results/simulation/SIM-010_observability_regression.json"
    failures: list[str] = []
    try:
        index = read_json(index_path)
    except Exception as exc:
        index, failures = {}, [f"SIM-010 index unreadable: {exc}"]
    index_rows = index.get("accepted_source_index")
    rows: dict[str, dict[str, Any]] = {}
    if not isinstance(index_rows, list):
        failures.append("SIM-010 index has no accepted-source list")
    else:
        for row in index_rows:
            if not isinstance(row, dict) or not isinstance(row.get("short_task_id"), str):
                failures.append("SIM-010 index has malformed source row")
                continue
            short = row["short_task_id"]
            if short in rows:
                failures.append(f"{short}: duplicate source-index binding")
            else:
                rows[short] = row
        unexpected = set(rows) - (set(TASKS) - {"SIM-010"})
        if unexpected:
            failures.append(f"SIM-010 index has unexpected source identities: {sorted(unexpected)}")
    bindings: dict[str, Any] = {}
    sources: dict[str, dict[str, Any]] = {}
    for short, expected in TASKS.items():
        apath = root / f"results/reviews/{short}_acceptance.json"
        record: dict[str, Any] = {"acceptance_path": str(apath.relative_to(root)), "status": "FAIL"}
        try:
            acceptance = read_json(apath)
            if acceptance.get("task_id") != f"TASK-{short}":
                raise ValueError("acceptance task identity mismatch")
            if acceptance.get("short_task_id") not in (None, short):
                raise ValueError("acceptance short task identity mismatch")
            record["accepted"] = accepted(acceptance)
            if not record["accepted"]: failures.append(f"{short}: not accepted")
            row = rows.get(short)
            if short != "SIM-010" and not row: failures.append(f"{short}: missing source-index binding")
            if short != "SIM-010" and row is not None:
                if row.get("acceptance_path") != str(apath.relative_to(root)):
                    raise ValueError("source-index acceptance path mismatch")
                if row.get("acceptance_sha256") != sha256(apath):
                    raise ValueError("contradictory source-index binding")
                if row.get("accepted_commit") != acceptance.get("accepted_commit", acceptance.get("reviewed_commit")):
                    raise ValueError("contradictory source-index binding")
            ev = acceptance.get("evidence") if isinstance(acceptance.get("evidence"), dict) else (row or {})
            path, digest = ev.get("path", ev.get("evidence_path")), ev.get("sha256", ev.get("evidence_sha256"))
            if not isinstance(path, str) or not isinstance(digest, str): raise ValueError("missing immutable Evidence binding")
            epath = root / path
            if sha256(epath) != digest: raise ValueError("Evidence hash mismatch")
            if row and (row.get("evidence_path") != path or row.get("evidence_sha256") != digest):
                raise ValueError("contradictory source-index binding")
            evidence = read_json(epath)
            record.update({"status": "PASS", "evidence_path": path, "evidence_sha256": digest,
                           "reviewed_revision": acceptance.get("accepted_commit", acceptance.get("reviewed_commit")),
                           "result": evidence_result(evidence), "required_result": expected})
            if evidence_result(evidence) != expected: failures.append(f"{short}: required READY result not proven")
            sources[short] = evidence
        except Exception as exc:
            record["reason"] = str(exc); failures.append(f"{short}: {exc}")
        bindings[short] = record
    declared = index.get("predicate_sources")
    predicates: dict[str, Any] = {}
    for name, (owner, check) in PREDICATES.items():
        # The source index must explicitly identify ownership: never guess from task/file names.
        if not isinstance(declared, dict) or declared.get(name) != owner:
            predicates[name] = {"expected": False if name in {"forbidden_state_transition", "leaked_process", "physical_dependency", "dual_world_cosimulation_required"} else "PASS", "actual": None, "source_tasks": [owner], "acceptance_artifacts": [bindings[owner]["acceptance_path"]], "underlying_evidence_paths": [bindings[owner].get("evidence_path")], "verified_bindings": [bindings[owner].get("evidence_sha256")], "reconstruction_status": "UNVERIFIED", "reason": "source index lacks unique predicate-source binding"}
            continue
        ok = owner in sources and bool(check(sources[owner]))
        expected = False if name in {"forbidden_state_transition", "leaked_process", "physical_dependency", "dual_world_cosimulation_required"} else "PASS"
        actual = (not ok) if isinstance(expected, bool) else ("PASS" if ok else "FAIL")
        predicates[name] = {"expected": expected, "actual": actual, "source_tasks": [owner], "acceptance_artifacts": [bindings[owner]["acceptance_path"]], "underlying_evidence_paths": [bindings[owner].get("evidence_path")], "verified_bindings": [bindings[owner].get("evidence_sha256")], "reconstruction_status": "PASS" if ok else "FAIL", "reason": None if ok else "underlying accepted Evidence did not prove predicate"}
    decision = "SIM_E2E_QUALIFIED" if not failures and all(x["reconstruction_status"] == "PASS" for x in predicates.values()) else "SIM_E2E_NOT_QUALIFIED"
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, text=True, capture_output=True).stdout.strip() or None
    return {"schema_version": 1, "task_id": "TASK-SIM-E2E", "decision": decision, "evaluation_repo_head": head,
            "verifier_identity_or_version": "verify_simulation_e2e_qualification.py/v1", "verifier_sha256_or_equivalent_immutable_identity": sha256(Path(__file__)),
            "predecessors": bindings, "accepted_evidence_bindings": bindings, "sim010_source_index_binding": {"path": str(index_path.relative_to(root)), "sha256": sha256(index_path) if index_path.exists() else None},
            "matrix": predicates, "failures": failures, "authorization_snapshot": {"TASK-W1-001 authorized": False, "TASK-W1-002 authorized": False, "Dataset V1 authorized": False, "SmolVLA fine-tuning authorized": False, "physical motion authorized": False, "hardware target frozen": False},
            "physical_dependency": False, "integrated_world_authority": "Gazebo", "mujoco_role": "component-bench", "dual_world_cosimulation_required": False,
            "validation_commands": ["PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider tests/test_simulation_e2e_qualification.py"]}

def evaluate_current(root: Path) -> dict[str, Any]:
    """Consume an explicitly declared additive chain, otherwise historical inputs."""
    if (Path(root) / "configs/simulation/e2e_successor_chain_v1.json").exists():
        package_root = str(Path(__file__).resolve().parents[1])
        if package_root not in sys.path:
            sys.path.insert(0, package_root)
        from scripts.simulation_e2e_successor import evaluate_successor
        return evaluate_successor(Path(root))
    return evaluate(Path(root))

def write_artifacts(result: dict[str, Any], output: Path, report: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True); report.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    bad = [name for name, row in result["matrix"].items() if row["reconstruction_status"] != "PASS"]
    report.write_text(f"# Simulation E2E qualification\n\nDecision: `{result['decision']}`\n\nUnverified or failed predicates: {', '.join(bad) or 'none'}.\n\nAll original Week, physical, training, and hardware-freeze authorizations remain `false`. Gazebo is the integrated world; MuJoCo remains a component bench; dual-world co-simulation is not required.\n", encoding="utf-8")

def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1]); parser.add_argument("--output", type=Path); parser.add_argument("--report", type=Path)
    args = parser.parse_args(); result = evaluate_current(args.root)
    if args.output or args.report:
        write_artifacts(result, args.output or args.root / "results/simulation/SIM-E2E_qualification.json", args.report or args.root / "docs/simulation/simulation_e2e_qualification_v1.md")
    print(result["decision"])
    return 0

if __name__ == "__main__": raise SystemExit(main())
