from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.verify_simulation_e2e_qualification import PREDICATES, TASKS, evaluate


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _sim009_scenarios() -> list[dict[str, object]]:
    fail_closed = {
        "SIM009-L0-MALFORMED": ("L0", "malformed", "INVALID_NAVIGATION_REQUEST"),
        "SIM009-L0-UNAVAILABLE": ("L0", "unavailable", "NAVIGATION_UNAVAILABLE"),
        "SIM009-NAV-BLOCKED": ("L1-NAV", "failure", "NAVIGATION_ABORTED"),
        "SIM009-NAV-ABORTED": ("L1-NAV", "failure", "NAVIGATION_ABORTED"),
        "SIM009-NAV-TF-UNAVAILABLE": ("L1-NAV", "failure", "NAVIGATION_TF_UNAVAILABLE"),
        "SIM009-VLA-GRASP-MISS": ("L1-VLA", "failure", "GRASP_MISS"),
        "SIM009-VLA-CONTACT-LOSS": ("L1-VLA", "failure", "CONTACT_LOSS"),
        "SIM009-VLA-WORKSPACE-LIMIT": ("L1-VLA", "failure", "WORKSPACE_LIMIT"),
        "SIM009-VLA-AMBIGUOUS": ("L1-VLA", "uncertain", "INVALID_OBSERVATION"),
    }
    rows = [
        {
            "id": scenario_id, "layer": layer, "outcome_kind": outcome_kind,
            "expected_decision": "FAIL_CLOSED", "decision": "FAIL_CLOSED", "pass": True,
            "within_budget": True, "cleanup_complete": True,
            "result": {"result": "failure", "status": "failed", "operation": "navigation.execute" if layer != "L1-VLA" else "vla.execute", "error": {"code": code}},
        }
        for scenario_id, (layer, outcome_kind, code) in fail_closed.items()
    ]
    rows.append({
        "id": "SIM009-L0-CONTRADICTORY", "layer": "L0", "outcome_kind": "contradictory",
        "expected_decision": "FAIL_CLOSED", "decision": "FAIL_CLOSED", "pass": True,
        "within_budget": True, "cleanup_complete": True, "validation_error": "result/status contradiction rejected",
    })
    rows.append({
        "id": "SIM009-NAV-TIMEOUT-RETRY", "layer": "L1-NAV", "outcome_kind": "unknown",
        "expected_decision": "RETRY", "decision": "RETRY", "pass": True,
        "within_budget": True, "cleanup_complete": True, "logical_side_effect_count": 1,
        "first_result": {"action_id": "nav-action", "mission_id": "nav-mission", "result": "pending", "status": "unknown", "error": {"code": "NAVIGATION_TIMEOUT", "retryable": True}},
        "reconciliation": {"action_id": "nav-action", "mission_id": "nav-mission", "operation": "action_status.get", "result": "success", "status": "succeeded", "observed_status": "failed"},
        "retry_authorization": {"action_id": "nav-action", "mission_id": "nav-mission", "reconciliation_completed": True, "resolved_status": "failed", "next_attempt": 2, "error": {"code": "NAVIGATION_ABORTED", "retryable": True}},
        "identity": {"action_id_stable": True, "mission_id_stable": True, "idempotency_key_stable": True, "attempt_incremented": True, "retry_request_id_new": True},
        "retry_result": {"action_id": "nav-action", "mission_id": "nav-mission", "result": "success", "status": "succeeded"},
    })
    for scenario_id, code, observed_status in (
        ("SIM009-VLA-TIMEOUT", "MUJOCO_TIMEOUT", "unknown"),
        ("SIM009-VLA-UNKNOWN", "MUJOCO_OUTCOME_UNKNOWN", "succeeded"),
    ):
        rows.append({
            "id": scenario_id, "layer": "L1-VLA", "outcome_kind": "unknown",
            "expected_decision": "RECONCILE", "decision": "RECONCILE", "pass": True,
            "within_budget": True, "cleanup_complete": True,
            "result": {"action_id": f"{scenario_id}-action", "mission_id": f"{scenario_id}-mission", "operation": "vla.execute", "result": "pending", "status": "unknown", "error": {"code": code, "retryable": True}},
            "reconciliation": {"action_id": f"{scenario_id}-action", "mission_id": f"{scenario_id}-mission", "operation": "action_status.get", "result": "success", "status": "succeeded", "observed_status": observed_status},
        })
    for scenario_id, decision, outcome_kind, verdict, mission_state, mission_outcome, path in (
        ("SIM009-VERIFY-MISMATCH", "RECOVERY", "failure", "fail", "recovering", "in_progress", ["executing", "reconciling", "recovering"]),
        ("SIM009-VERIFY-STALE", "HITL", "failure", None, "escalated", "requires_human", ["executing", "escalated"]),
        ("SIM009-VERIFY-UNCERTAIN", "RECONCILE", "uncertain", "uncertain", "reconciling", "in_progress", ["executing", "reconciling"]),
    ):
        verification = {"operation": "verification.verify", "result": "success", "status": "succeeded", "verdict": verdict}
        if scenario_id == "SIM009-VERIFY-MISMATCH":
            verification["mismatch_code"] = "EXPECTED_STATE_MISMATCH"
        if scenario_id == "SIM009-VERIFY-UNCERTAIN":
            verification["mismatch_code"] = "INSUFFICIENT_OR_AMBIGUOUS_EVIDENCE"
        if scenario_id == "SIM009-VERIFY-STALE":
            verification = {"operation": "verification.verify", "result": "failure", "status": "failed", "error": {"code": "INVALID_VERIFICATION_EVIDENCE"}}
        rows.append({
            "id": scenario_id, "layer": "L2", "outcome_kind": outcome_kind,
            "expected_decision": decision, "decision": decision, "route": decision, "pass": True,
            "within_budget": True, "cleanup_complete": True,
            "skill_reported_success": scenario_id == "SIM009-VERIFY-MISMATCH",
            "verification": verification,
            "mission": {"mission_success_committed": False, "mission_state": mission_state, "mission_outcome": mission_outcome, "verification_verdict": verdict, "transition_path": path, "transition": {"from": "executing", "to": mission_state}},
        })
    for row in rows:
        row.setdefault("mission", {"mission_success_committed": False})
    return rows


def _fixture(root: Path) -> None:
    (root / "results/reviews").mkdir(parents=True)
    (root / "results/simulation").mkdir(parents=True)
    data = {
        "SIM-003": {"baseline_id": "SIM_BASELINE_V1", "deterministic_regression": {"status": "PASS"}},
        "SIM-004": {"scenarios": [{"id": "timeout_reconciliation", "pass": True}], "runtime": "ros2 jazzy gazebo"},
        "SIM-005": {"l0_regression": "PASS", "scenarios": [{"result": "failure"}, {"result": "failure"}], "provenance": {"model": "x"}},
        "SIM-006": {"normalized_sources": ["gazebo", "mujoco"], "proof": {"uncertain_confidence_promotion": "forbidden"}},
        "SIM-007": {"profiles": {"system": {"integrated_world": "gazebo_harmonic"}}},
        "SIM-008": {},
        "SIM-009": {"scenarios": [{"id": "NAV", "pass": True}], "cleanup_complete": True},
        "SIM-010": {"deterministic_replay": {"status": "PASS"}, "full_repository_regression": {"gate_result": "PASS"}, "simulation_only": True},
    }
    data["SIM-003"].update({"implementation_complete": True, "deterministic_regression": {"status": "PASS", "probe": {"returncode": 0}}})
    data["SIM-004"].update({
        "runtime_identity": {"gazebo": {"returncode": 0}, "ros2": {"command": ["/opt/ros/jazzy/bin/ros2"]}},
        "scenarios": [
            *[{"id": name, "pass": True} for name in ("success", "invalid_goal", "unavailable", "blocked")],
            {"id": "timeout_reconciliation", "pass": True, "status": {"operation": "action_status.get", "observed_status": "unknown"}},
        ],
    })
    data["SIM-005"].update({
        "cleanup": {"bounded": True, "child_processes": 0},
        "provenance": {"backend_id": "sim005-mujoco-vla-backend-v1", "physical_target": False, "assets": [{"path": f"asset-{n}", "sha256": "a" * 64} for n in range(3)]},
        "scenarios": [{"scenario": name, "pass": True} for name in ("mujoco-grasp-miss", "mujoco-contact-loss", "mujoco-workspace-limit", "mujoco-invalid-observation")],
    })
    data["SIM-006"].update({"proof": {"cross_backend_equivalence": "equivalent incomplete Gazebo and MuJoCo evidence produces uncertain", "uncertain_confidence_promotion": "forbidden", "insufficient_or_ambiguous": "uncertain"}})
    data["SIM-007"].update({"system_authority": {"integrated_world": "gazebo_harmonic", "dual_world": False, "mujoco_live_world": False}})
    data["SIM-008"].update({"execution": {"mission": {"result": "success", "status": "completed"}, "lifecycle": {"cleanup_complete": True}, "steps": [{"name": name} for name in ("source_navigation", "source_verification", "destination_navigation", "vla.execute", "final_verification")]}})
    data["SIM-009"].update({"cleanup_complete": True, "simulation_authority": {"physical_dependency": False}, "scenarios": _sim009_scenarios()})
    data["SIM-010"].update({"deterministic_replay": {"status": "PASS", "failures": []}, "normal_failure_suite_coverage": {"status": "PASS"}, "physics_semantic_regression": {"status": "PASS"}})
    index = {"accepted_source_index": [], "predicate_sources": {key: value[0] for key, value in PREDICATES.items()}}
    for short, ready in TASKS.items():
        evidence = {"task_id": f"TASK-{short}", "task_specific_result": ready, **data[short]}
        ep = root / f"results/simulation/{short}.json"; ep.write_text(json.dumps(evidence))
        acceptance = {"task_id": f"TASK-{short}", "status": "ACCEPT", "accepted_commit": short * 5, "evidence": {"path": str(ep.relative_to(root)), "sha256": _sha(ep)}}
        ap = root / f"results/reviews/{short}_acceptance.json"; ap.write_text(json.dumps(acceptance))
        if short != "SIM-010": index["accepted_source_index"].append({"short_task_id": short, "acceptance_path": str(ap.relative_to(root)), "acceptance_sha256": _sha(ap), "accepted_commit": acceptance["accepted_commit"], "evidence_path": str(ep.relative_to(root)), "evidence_sha256": _sha(ep)})
    (root / "results/simulation/SIM-010_observability_regression.json").write_text(json.dumps(index))


def test_valid_explicit_source_chains_qualify(tmp_path: Path) -> None:
    _fixture(tmp_path)
    assert evaluate(tmp_path)["decision"] == "SIM_E2E_QUALIFIED"


def test_tampered_evidence_fails_closed_without_mutation(tmp_path: Path) -> None:
    _fixture(tmp_path)
    target = tmp_path / "results/simulation/SIM-005.json"; target.write_text("{}")
    result = evaluate(tmp_path)
    assert result["decision"] == "SIM_E2E_NOT_QUALIFIED"
    assert any("hash mismatch" in x.lower() for x in result["failures"])


def test_diagnostic_lookalike_cannot_repair_failed_immutable_binding(tmp_path: Path) -> None:
    _fixture(tmp_path)
    (tmp_path / "results/simulation/SIM-005_mujoco_vla_backend.json").write_text(json.dumps({"task_specific_result": "SIM_MANIPULATION_BACKEND_READY"}))
    (tmp_path / "results/simulation/SIM-005.json").write_text("{}")
    assert evaluate(tmp_path)["decision"] == "SIM_E2E_NOT_QUALIFIED"


def test_missing_explicit_predicate_index_cannot_be_repaired_by_top_level_ready(tmp_path: Path) -> None:
    _fixture(tmp_path)
    index_path = tmp_path / "results/simulation/SIM-010_observability_regression.json"
    index = json.loads(index_path.read_text()); index.pop("predicate_sources"); index_path.write_text(json.dumps(index))
    assert evaluate(tmp_path)["decision"] == "SIM_E2E_NOT_QUALIFIED"


def test_contradictory_reviewed_revision_in_source_index_fails_closed(tmp_path: Path) -> None:
    _fixture(tmp_path)
    ip = tmp_path / "results/simulation/SIM-010_observability_regression.json"
    index = json.loads(ip.read_text())
    next(x for x in index["accepted_source_index"] if x["short_task_id"] == "SIM-004")["accepted_commit"] = "stale"
    ip.write_text(json.dumps(index))
    result = evaluate(tmp_path)
    assert result["decision"] == "SIM_E2E_NOT_QUALIFIED"
    assert any("contradictory source-index" in x for x in result["failures"])


def test_duplicate_source_index_identity_fails_closed(tmp_path: Path) -> None:
    _fixture(tmp_path)
    index_path = tmp_path / "results/simulation/SIM-010_observability_regression.json"
    index = json.loads(index_path.read_text())
    index["accepted_source_index"].append(dict(index["accepted_source_index"][0]))
    index_path.write_text(json.dumps(index))
    assert evaluate(tmp_path)["decision"] == "SIM_E2E_NOT_QUALIFIED"


def test_mismatched_acceptance_identity_fails_closed(tmp_path: Path) -> None:
    _fixture(tmp_path)
    acceptance_path = tmp_path / "results/reviews/SIM-004_acceptance.json"
    acceptance = json.loads(acceptance_path.read_text())
    acceptance["task_id"] = "TASK-SIM-005"
    acceptance_path.write_text(json.dumps(acceptance))
    index_path = tmp_path / "results/simulation/SIM-010_observability_regression.json"
    index = json.loads(index_path.read_text())
    row = next(row for row in index["accepted_source_index"] if row["short_task_id"] == "SIM-004")
    row["acceptance_sha256"] = _sha(acceptance_path)
    index_path.write_text(json.dumps(index))
    assert evaluate(tmp_path)["decision"] == "SIM_E2E_NOT_QUALIFIED"


def test_missing_state_safety_proof_fails_closed(tmp_path: Path) -> None:
    _fixture(tmp_path)
    evidence_path = tmp_path / "results/simulation/SIM-009.json"
    evidence = json.loads(evidence_path.read_text())
    for row in evidence["scenarios"]:
        row.pop("mission", None)
    evidence_path.write_text(json.dumps(evidence))
    acceptance_path = tmp_path / "results/reviews/SIM-009_acceptance.json"
    acceptance = json.loads(acceptance_path.read_text())
    acceptance["evidence"]["sha256"] = _sha(evidence_path)
    acceptance_path.write_text(json.dumps(acceptance))
    index_path = tmp_path / "results/simulation/SIM-010_observability_regression.json"
    index = json.loads(index_path.read_text())
    row = next(row for row in index["accepted_source_index"] if row["short_task_id"] == "SIM-009")
    row.update({"acceptance_sha256": _sha(acceptance_path), "evidence_sha256": _sha(evidence_path)})
    index_path.write_text(json.dumps(index))
    assert evaluate(tmp_path)["decision"] == "SIM_E2E_NOT_QUALIFIED"


def _rebind_sim009(root: Path) -> None:
    evidence_path = root / "results/simulation/SIM-009.json"
    acceptance_path = root / "results/reviews/SIM-009_acceptance.json"
    acceptance = json.loads(acceptance_path.read_text())
    acceptance["evidence"]["sha256"] = _sha(evidence_path)
    acceptance_path.write_text(json.dumps(acceptance))
    index_path = root / "results/simulation/SIM-010_observability_regression.json"
    index = json.loads(index_path.read_text())
    row = next(row for row in index["accepted_source_index"] if row["short_task_id"] == "SIM-009")
    row.update({"acceptance_sha256": _sha(acceptance_path), "evidence_sha256": _sha(evidence_path)})
    index_path.write_text(json.dumps(index))


def test_sim009_sparse_or_contradictory_semantics_fail_closed(tmp_path: Path) -> None:
    cases = (
        ("SIM009-NAV-BLOCKED", "outcome_kind"),
        ("SIM009-NAV-BLOCKED", "expected_decision"),
        ("SIM009-NAV-BLOCKED", "result.error.code"),
        ("SIM009-NAV-TIMEOUT-RETRY", "retry_authorization"),
        ("SIM009-NAV-TIMEOUT-RETRY", "identity.idempotency_key_stable"),
        ("SIM009-VLA-TIMEOUT", "reconciliation"),
        ("SIM009-VERIFY-MISMATCH", "mission.transition_path"),
        ("SIM009-VERIFY-UNCERTAIN", "verification.verdict"),
        ("SIM009-VERIFY-STALE", "cleanup_complete"),
        ("SIM009-VERIFY-STALE", "within_budget"),
    )
    for index, (scenario_id, field) in enumerate(cases):
        case_root = tmp_path / str(index)
        _fixture(case_root)
        evidence_path = case_root / "results/simulation/SIM-009.json"
        evidence = json.loads(evidence_path.read_text())
        row = next(row for row in evidence["scenarios"] if row["id"] == scenario_id)
        target = row
        parts = field.split(".")
        for key in parts[:-1]:
            target = target[key]
        target.pop(parts[-1])
        evidence_path.write_text(json.dumps(evidence))
        _rebind_sim009(case_root)
        assert evaluate(case_root)["decision"] == "SIM_E2E_NOT_QUALIFIED", f"{scenario_id} missing {field} qualified"


def test_blocked_or_wrong_ready_predecessor_fails_closed(tmp_path: Path) -> None:
    _fixture(tmp_path)
    ep = tmp_path / "results/simulation/SIM-007.json"; data = json.loads(ep.read_text()); data.update({"task_specific_result": "SIM_MISSION_INTEGRATION_BLOCKED", "qualified": True, "status": "PASS"}); ep.write_text(json.dumps(data))
    # Refresh only the acceptance and source index binding: semantic wrong READY must still fail.
    ap = tmp_path / "results/reviews/SIM-007_acceptance.json"; a = json.loads(ap.read_text()); a["evidence"]["sha256"] = _sha(ep); ap.write_text(json.dumps(a))
    ip = tmp_path / "results/simulation/SIM-010_observability_regression.json"; i = json.loads(ip.read_text())
    row = next(x for x in i["accepted_source_index"] if x["short_task_id"] == "SIM-007"); row.update({"acceptance_sha256": _sha(ap), "evidence_sha256": _sha(ep)})
    ip.write_text(json.dumps(i))
    assert evaluate(tmp_path)["decision"] == "SIM_E2E_NOT_QUALIFIED"


def test_cli_emits_only_decision_on_stdout_and_exit_zero(tmp_path: Path) -> None:
    _fixture(tmp_path)
    completed = subprocess.run([sys.executable, str(ROOT / "scripts/verify_simulation_e2e_qualification.py"), "--root", str(tmp_path)], text=True, capture_output=True)
    assert completed.returncode == 0
    assert completed.stdout == "SIM_E2E_QUALIFIED\n"
