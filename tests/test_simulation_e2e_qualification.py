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
