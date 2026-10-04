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
PREDICATES = {
    "sim_baseline_bound": ("SIM-003", lambda d: d.get("baseline_id") == "SIM_BASELINE_V1"),
    "accepted_contract_regression": ("SIM-003", lambda d: d.get("deterministic_regression", {}).get("status") == "PASS"),
    "L0_contract_runtime": ("SIM-005", lambda d: d.get("l0_regression") == "PASS"),
    "timeout_reconciliation": ("SIM-004", lambda d: any(x.get("id") == "timeout_reconciliation" and x.get("pass") is True for x in d.get("scenarios", []))),
    "ros2_jazzy_gazebo_navigation": ("SIM-004", lambda d: "jazzy" in json.dumps(d).lower() and "gazebo" in json.dumps(d).lower()),
    "normal_system_e2e": ("SIM-008", lambda d: d.get("task_specific_result") == "SIM_NORMAL_E2E_READY"),
    "required_navigation_system_failures": ("SIM-009", lambda d: any("NAV" in str(x.get("id")) and x.get("pass") is True for x in d.get("scenarios", []))),
    "manipulation_backend": ("SIM-005", lambda d: bool(d.get("scenarios"))),
    "required_manipulation_failures": ("SIM-005", lambda d: sum(x.get("result") == "failure" for x in d.get("scenarios", [])) >= 2),
    "model_config_provenance": ("SIM-005", lambda d: bool(d.get("provenance") or d.get("source_hashes"))),
    "cross_simulator_verification": ("SIM-006", lambda d: set(d.get("normalized_sources", [])) >= {"gazebo", "mujoco"}),
    "uncertain_never_auto_success": ("SIM-006", lambda d: d.get("proof", {}).get("uncertain_confidence_promotion") == "forbidden"),
    "required_failure_cases": ("SIM-009", lambda d: len(d.get("scenarios", [])) > 0 and all(x.get("pass") is True for x in d.get("scenarios", []))),
    "forbidden_state_transition": ("SIM-009", lambda d: "forbidden_state_transition" not in json.dumps(d).lower()),
    "leaked_process": ("SIM-009", lambda d: d.get("cleanup_complete") is True),
    "evidence_reproducible": ("SIM-010", lambda d: d.get("deterministic_replay", {}).get("status") == "PASS"),
    "regression_green": ("SIM-010", lambda d: d.get("full_repository_regression", {}).get("gate_result") == "PASS"),
    "observability_sufficient": ("SIM-010", lambda d: d.get("task_specific_result") == "SIM_OBSERVABILITY_REGRESSION_READY"),
    "physical_dependency": ("SIM-010", lambda d: d.get("simulation_only") is True),
    "dual_world_cosimulation_required": ("SIM-007", lambda d: all(x.get("integrated_world") != "dual_world" for x in d.get("profiles", {}).values())),
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
    rows = {str(x.get("short_task_id")): x for x in index.get("accepted_source_index", []) if isinstance(x, dict)}
    bindings: dict[str, Any] = {}
    sources: dict[str, dict[str, Any]] = {}
    for short, expected in TASKS.items():
        apath = root / f"results/reviews/{short}_acceptance.json"
        record: dict[str, Any] = {"acceptance_path": str(apath.relative_to(root)), "status": "FAIL"}
        try:
            acceptance = read_json(apath)
            record["accepted"] = accepted(acceptance)
            if not record["accepted"]: failures.append(f"{short}: not accepted")
            row = rows.get(short)
            if short != "SIM-010" and not row: failures.append(f"{short}: missing source-index binding")
            ev = acceptance.get("evidence") if isinstance(acceptance.get("evidence"), dict) else (row or {})
            path, digest = ev.get("path", ev.get("evidence_path")), ev.get("sha256", ev.get("evidence_sha256"))
            if not isinstance(path, str) or not isinstance(digest, str): raise ValueError("missing immutable Evidence binding")
            epath = root / path
            if sha256(epath) != digest: raise ValueError("Evidence hash mismatch")
            if row and (row.get("acceptance_sha256") != sha256(apath) or row.get("evidence_path") != path or row.get("evidence_sha256") != digest or row.get("accepted_commit") != acceptance.get("accepted_commit", acceptance.get("reviewed_commit"))):
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

def write_artifacts(result: dict[str, Any], output: Path, report: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True); report.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    bad = [name for name, row in result["matrix"].items() if row["reconstruction_status"] != "PASS"]
    report.write_text(f"# Simulation E2E qualification\n\nDecision: `{result['decision']}`\n\nUnverified or failed predicates: {', '.join(bad) or 'none'}.\n\nAll original Week, physical, training, and hardware-freeze authorizations remain `false`. Gazebo is the integrated world; MuJoCo remains a component bench; dual-world co-simulation is not required.\n", encoding="utf-8")

def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1]); parser.add_argument("--output", type=Path); parser.add_argument("--report", type=Path)
    args = parser.parse_args(); result = evaluate(args.root)
    if args.output or args.report:
        write_artifacts(result, args.output or args.root / "results/simulation/SIM-E2E_qualification.json", args.report or args.root / "docs/simulation/simulation_e2e_qualification_v1.md")
    print(result["decision"])
    return 0

if __name__ == "__main__": raise SystemExit(main())
