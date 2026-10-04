import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "codex" / "run_task_orchestrator.py"
spec = importlib.util.spec_from_file_location("orch", MODULE_PATH)
orch = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = orch
assert spec.loader is not None
spec.loader.exec_module(orch)


def test_load_staged_contract(tmp_path):
    path = tmp_path / "tasks" / "orchestrator"
    path.mkdir(parents=True)
    (path / "TASK-SIM-011.json").write_text(json.dumps({
        "schema_version": 1,
        "task_id": "TASK-SIM-011",
        "profile": "staged_integration_v1",
        "gates": [{"id": "G0", "command": ["python3", "gate.py"]}],
        "protected_paths": ["results/reviews/SIM-009_acceptance.json"],
        "source_paths": ["scripts/sim011.py"],
        "canonical": {"command": ["python3", "canonical.py"], "evidence_paths": ["results/sim011.json"]},
        "literal_validation": [["python3", "-m", "pytest", "-q"]],
    }), encoding="utf-8")
    contract = orch.load_task_orchestrator_contract(tmp_path, "TASK-SIM-011")
    assert contract is not None
    assert contract.profile == "staged_integration_v1"
    assert contract.gates[0]["id"] == "G0"


def test_upgrade_v2_checkpoint_to_v3_preserves_existing_state():
    state = {"schema_version": 2, "task_id": "TASK-SIM-011", "phase": "implementation", "fix_cycles_used": 1}
    upgraded = orch.upgrade_checkpoint_state(state, staged=True)
    assert upgraded["schema_version"] == 3
    assert upgraded["fix_cycles_used"] == 1
    assert upgraded["gate_state"]["current_gate_index"] == 0
    assert upgraded["aggregate"]["orchestrator_runs"] == 0


def test_phase_after_implementation_is_staged_only():
    assert orch.phase_after_implementation(staged=True) == "gate_resolution"
    assert orch.phase_after_implementation(staged=False) == "review"


def _gate_state():
    return orch.upgrade_checkpoint_state({"schema_version": 2}, staged=True)["gate_state"]


def test_gate_blocker_signature_ignores_message_wording():
    a = {
        "gate_id": "G4", "finding_id": "F-1", "root_cause_class": "CORRELATION",
        "first_failing_invariant": "request_identity", "affected_boundary": "collector",
        "classification": "SAME_GATE", "message": "first wording",
    }
    b = {**a, "message": "different wording"}
    assert orch.gate_blocker_signature(a) == orch.gate_blocker_signature(b)


def test_gate_failure_allows_two_bounded_fixes_then_escalates_on_third_same_invariant():
    gs = _gate_state()
    blocker = {
        "gate_id": "G4", "finding_id": "F-1", "root_cause_class": "CORRELATION",
        "first_failing_invariant": "request_identity", "affected_boundary": "collector",
        "classification": "SAME_GATE",
    }
    assert orch.register_gate_failure(gs, blocker, max_attempts=3) == "FIX"
    assert orch.register_gate_failure(gs, blocker, max_attempts=3) == "FIX"
    assert orch.register_gate_failure(gs, blocker, max_attempts=3) == "ARCHITECTURE_REVIEW_REQUIRED"


def test_external_gate_failure_stops_without_fix():
    gs = _gate_state()
    blocker = {
        "gate_id": "G2", "finding_id": "EXT-1", "root_cause_class": "NETWORK",
        "first_failing_invariant": "simulator_reachable", "affected_boundary": "runtime",
        "classification": "NEW_EXTERNAL_FAULT_DOMAIN",
    }
    assert orch.register_gate_failure(gs, blocker) == "STOP"
    assert gs["blocker_attempt_counts"] == {}


def test_mark_gate_pass_freezes_baseline_and_advances_cursor():
    gs = _gate_state()
    orch.mark_gate_pass(gs, "G0", {"head": "abc", "result_sha256": "123"})
    assert gs["current_gate_index"] == 1
    assert gs["passed_gates"]["G0"]["head"] == "abc"


def test_begin_new_gate_attempt_invalidates_supplier_cache_but_not_passed_gates():
    gs = _gate_state()
    gs["passed_gates"]["G0"] = {"status": "PASS"}
    gs["supplier_cache"]["attempt-1:sim009"] = {"path": "x"}
    orch.begin_new_gate_attempt(gs)
    assert gs["attempt_id"] == 2
    assert gs["supplier_cache"] == {}
    assert "G0" in gs["passed_gates"]


def _init_git_repo(path: Path):
    import subprocess
    subprocess.run(["git", "init", "-q"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=path, check=True)
    (path / "scripts").mkdir(exist_ok=True)
    (path / "scripts" / "app.py").write_text("x = 1\n", encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=path, check=True)
    subprocess.run(["git", "commit", "-qm", "base"], cwd=path, check=True)


def test_source_finalization_creates_immutable_commit_and_hashes(tmp_path):
    _init_git_repo(tmp_path)
    (tmp_path / "scripts" / "app.py").write_text("x = 2\n", encoding="utf-8")
    commit, hashes = orch.commit_source_finalization(
        tmp_path, task_id="TASK-SIM-011", source_paths=("scripts/app.py",)
    )
    assert commit == orch.run_git(tmp_path, "rev-parse", "HEAD").stdout.strip()
    assert hashes["scripts/app.py"] == orch.git_path_sha256(tmp_path, commit, "scripts/app.py")
    assert orch.worktree_status(tmp_path) == ""


def test_source_finalization_rejects_dirty_path_outside_source_scope(tmp_path):
    _init_git_repo(tmp_path)
    (tmp_path / "scripts" / "app.py").write_text("x = 2\n", encoding="utf-8")
    (tmp_path / "unexpected.txt").write_text("oops\n", encoding="utf-8")
    import pytest
    with pytest.raises(orch.OrchestratorError, match="SOURCE_FINALIZATION_SCOPE_VIOLATION"):
        orch.commit_source_finalization(
            tmp_path, task_id="TASK-SIM-011", source_paths=("scripts/app.py",)
        )


def test_canonical_evidence_source_sha_mismatch_is_rejected(tmp_path):
    _init_git_repo(tmp_path)
    commit = orch.run_git(tmp_path, "rev-parse", "HEAD").stdout.strip()
    results = tmp_path / "results"
    results.mkdir()
    (results / "evidence.json").write_text(json.dumps({
        "source_git_sha": "deadbeef",
        "source_hashes": {"scripts/app.py": orch.git_path_sha256(tmp_path, commit, "scripts/app.py")},
    }), encoding="utf-8")
    import pytest
    with pytest.raises(orch.OrchestratorError, match="source_git_sha mismatch"):
        orch.verify_canonical_evidence_bindings(tmp_path, commit, ("results/evidence.json",))


def test_canonical_evidence_declared_source_hash_mismatch_is_rejected(tmp_path):
    _init_git_repo(tmp_path)
    commit = orch.run_git(tmp_path, "rev-parse", "HEAD").stdout.strip()
    results = tmp_path / "results"
    results.mkdir()
    (results / "evidence.json").write_text(json.dumps({
        "source_git_sha": commit,
        "source_hashes": {"scripts/app.py": "bad"},
    }), encoding="utf-8")
    import pytest
    with pytest.raises(orch.OrchestratorError, match="source hash mismatch"):
        orch.verify_canonical_evidence_bindings(tmp_path, commit, ("results/evidence.json",))


def test_changed_paths_preserves_first_porcelain_path(tmp_path):
    _init_git_repo(tmp_path)
    (tmp_path / "scripts" / "app.py").write_text("x = 3\n", encoding="utf-8")
    assert orch.changed_paths(tmp_path) == ["scripts/app.py"]


def test_protected_artifact_guard_blocks_worktree_modification(tmp_path):
    _init_git_repo(tmp_path)
    protected = tmp_path / "results" / "reviews"
    protected.mkdir(parents=True)
    artifact = protected / "SIM-009_acceptance.json"
    artifact.write_text('{"status":"ACCEPT"}\n', encoding="utf-8")
    import subprocess
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-qm", "add protected"], cwd=tmp_path, check=True)
    snapshot = orch.snapshot_protected_artifacts(
        tmp_path, ("results/reviews/SIM-009_acceptance.json",)
    )
    artifact.write_text('{"status":"REJECT"}\n', encoding="utf-8")
    import pytest
    with pytest.raises(orch.OrchestratorError, match="PROTECTED_ARTIFACT_VIOLATION"):
        orch.assert_protected_artifacts_unchanged(
            tmp_path, ("results/reviews/SIM-009_acceptance.json",), snapshot
        )


def test_protected_artifact_guard_blocks_committed_rewrite(tmp_path):
    _init_git_repo(tmp_path)
    protected = tmp_path / "results" / "reviews"
    protected.mkdir(parents=True)
    artifact = protected / "SIM-009_acceptance.json"
    artifact.write_text('{"status":"ACCEPT"}\n', encoding="utf-8")
    import subprocess
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-qm", "add protected"], cwd=tmp_path, check=True)
    snapshot = orch.snapshot_protected_artifacts(
        tmp_path, ("results/reviews/SIM-009_acceptance.json",)
    )
    artifact.write_text('{"status":"REJECT"}\n', encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-qm", "rewrite protected"], cwd=tmp_path, check=True)
    import pytest
    with pytest.raises(orch.OrchestratorError, match="PROTECTED_ARTIFACT_VIOLATION"):
        orch.assert_protected_artifacts_unchanged(
            tmp_path, ("results/reviews/SIM-009_acceptance.json",), snapshot
        )


def test_protected_artifact_guard_allows_unprotected_change(tmp_path):
    _init_git_repo(tmp_path)
    protected = tmp_path / "results" / "reviews"
    protected.mkdir(parents=True)
    artifact = protected / "SIM-009_acceptance.json"
    artifact.write_text('{"status":"ACCEPT"}\n', encoding="utf-8")
    import subprocess
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-qm", "add protected"], cwd=tmp_path, check=True)
    snapshot = orch.snapshot_protected_artifacts(
        tmp_path, ("results/reviews/SIM-009_acceptance.json",)
    )
    (tmp_path / "scripts" / "app.py").write_text("x = 7\n", encoding="utf-8")
    orch.assert_protected_artifacts_unchanged(
        tmp_path, ("results/reviews/SIM-009_acceptance.json",), snapshot
    )


def test_literal_validation_records_executable_interpreter_and_git_sha(tmp_path):
    import sys
    _init_git_repo(tmp_path)
    result = orch.run_literal_validation(tmp_path, (sys.executable, "-c", "print('ok')"))
    assert result["exit_code"] == 0
    assert Path(result["resolved_executable"]).resolve() == Path(sys.executable).resolve()
    assert Path(result["interpreter"]).resolve() == Path(sys.executable).resolve()
    assert result["git_sha"] == orch.run_git(tmp_path, "rev-parse", "HEAD").stdout.strip()


def test_literal_validation_nonzero_exit_is_recorded(tmp_path):
    import sys
    _init_git_repo(tmp_path)
    result = orch.run_literal_validation(tmp_path, (sys.executable, "-c", "raise SystemExit(7)"))
    assert result["exit_code"] == 7


def test_accumulate_stage_record_updates_task_lifetime_metrics():
    state = orch.upgrade_checkpoint_state({"schema_version": 2}, staged=True)
    record = orch.StageRunRecord(
        task_id="TASK-SIM-011", role="diagnosis", model="gpt-5.6-sol",
        reasoning_effort="medium", started_at="now", tokens_reported=123,
    )
    orch.accumulate_stage_record(state, record, logical_role="diagnosis")
    assert state["aggregate"]["codex_calls"] == 1
    assert state["aggregate"]["reported_tokens_total"] == 123
    assert state["aggregate"]["diagnosis_calls"] == 1


def test_invalidate_staged_proof_clears_downstream_authority_but_preserves_protected_snapshot():
    state = orch.upgrade_checkpoint_state({"schema_version": 2}, staged=True)
    state["protected_artifacts"] = {"p": {"sha256": "x"}}
    state["gate_state"]["current_gate_index"] = 5
    state["gate_state"]["passed_gates"] = {"G0": {"status": "PASS"}}
    state["gate_state"]["supplier_cache"] = {"attempt-1:x": {}}
    state["finalization"]["source_commit"] = "abc"
    state["finalization"]["binding_verified"] = True
    state["literal_validation"]["results"] = [{"exit_code": 0}]
    orch.invalidate_staged_proof(state)
    assert state["gate_state"]["current_gate_index"] == 0
    assert state["gate_state"]["passed_gates"] == {}
    assert state["gate_state"]["supplier_cache"] == {}
    assert state["finalization"]["source_commit"] is None
    assert state["literal_validation"]["results"] == []
    assert state["protected_artifacts"] == {"p": {"sha256": "x"}}


def _model_policy():
    roles = {
        name: orch.ModelConfig(model="test-model", reasoning_effort="medium")
        for name in ("implementation", "review", "fix", "rereview", "diagnosis", "diagnosis_escalated")
    }
    classes = {
        name: orch.TaskClassConfig(
            diagnosis_required=False,
            allow_high_escalation=False,
            review_reasoning_effort="medium",
            rereview_reasoning_effort="medium",
        )
        for name in ("GREEN", "YELLOW", "RED")
    }
    return orch.ModelPolicy(
        roles=roles,
        task_classes=classes,
        classification=orch.ClassificationConfig(
            green_max_score=1,
            yellow_max_score=3,
            explicit_override_keys=("task_class",),
        ),
        acceptance_mode="deterministic",
    )


def _prepare_lifecycle_repo(path: Path, *, staged: bool):
    import subprocess, sys
    subprocess.run(["git", "init", "-q"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=path, check=True)
    (path / "tasks").mkdir(parents=True, exist_ok=True)
    (path / "tasks" / "TASK-SIM-011.md").write_text("task_class: GREEN\n", encoding="utf-8")
    (path / "scripts").mkdir(exist_ok=True)
    (path / "scripts" / "app.py").write_text("VALUE = 1\n", encoding="utf-8")
    if staged:
        (path / "tasks" / "orchestrator").mkdir(parents=True, exist_ok=True)
        (path / "results" / "reviews").mkdir(parents=True, exist_ok=True)
        (path / "results" / "reviews" / "SIM-009_acceptance.json").write_text(
            json.dumps({"task_id": "TASK-SIM-009", "status": "ACCEPT"}) + "\n",
            encoding="utf-8",
        )
        (path / "tools").mkdir(exist_ok=True)
        (path / "tools" / "canonical.py").write_text(
            "import json, pathlib, subprocess\n"
            "head=subprocess.check_output(['git','rev-parse','HEAD'], text=True).strip()\n"
            "p=pathlib.Path('results/evidence.json'); p.parent.mkdir(parents=True, exist_ok=True)\n"
            "p.write_text(json.dumps({'source_git_sha':head,'source_hashes':{}})+'\\n')\n",
            encoding="utf-8",
        )
        contract = {
            "schema_version": 1,
            "task_id": "TASK-SIM-011",
            "profile": "staged_integration_v1",
            "gates": [{"id": "G0", "command": [sys.executable, "-c", "print('gate')"]}],
            "protected_paths": ["results/reviews/SIM-009_acceptance.json"],
            "source_paths": [
                "scripts/app.py", "tools/canonical.py", "tasks/TASK-SIM-011.md",
                "tasks/orchestrator/TASK-SIM-011.json",
            ],
            "canonical": {
                "command": [sys.executable, "tools/canonical.py"],
                "evidence_paths": ["results/evidence.json"],
            },
            "literal_validation": [[sys.executable, "-c", "print('1 passed')"]],
        }
        (path / "tasks" / "orchestrator" / "TASK-SIM-011.json").write_text(
            json.dumps(contract, indent=2) + "\n", encoding="utf-8"
        )
    subprocess.run(["git", "add", "-A"], cwd=path, check=True)
    subprocess.run(["git", "commit", "-qm", "baseline"], cwd=path, check=True)


def _fake_stage_runner(call_roles):
    def fake(prompt, repo, config, *, ctx, task_id, role):
        call_roles.append(role)
        if role == "implementation":
            return orch.StageResult(task_id, "implementation", "COMPLETE", {
                "task_id": task_id, "stage": "implementation", "status": "COMPLETE", "workflow_complete": True
            })
        if role == "gate_fix":
            return orch.StageResult(task_id, "gate_fix", "READY_FOR_GATE_RERUN", {
                "task_id": task_id, "stage": "gate_fix", "status": "READY_FOR_GATE_RERUN", "workflow_complete": True
            })
        if role in {"review", "rereview"}:
            return orch.StageResult(task_id, "review", "ACCEPT", {
                "task_id": task_id, "stage": "review", "status": "ACCEPT", "workflow_complete": True
            })
        raise AssertionError(f"unexpected role {role}")
    return fake


def test_integrated_staged_lifecycle_resolves_two_same_gate_blockers_then_accepts(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    _prepare_lifecycle_repo(repo, staged=True)
    roles = []
    monkeypatch.setattr(orch, "run_stage", _fake_stage_runner(roles))
    sequence = [
        (False, {
            "gate_id": "G0", "finding_id": "A", "root_cause_class": "RUNTIME",
            "first_failing_invariant": "clock", "affected_boundary": "runtime", "classification": "SAME_GATE",
        }),
        (False, {
            "gate_id": "G0", "finding_id": "B", "root_cause_class": "RUNTIME",
            "first_failing_invariant": "action", "affected_boundary": "runtime", "classification": "SAME_GATE",
        }),
        (True, None),
    ]
    gate_calls = []
    def fake_gate(repo_path, gate):
        passed, blocker = sequence[len(gate_calls)]
        gate_calls.append(gate["id"])
        head = orch.run_git(repo_path, "rev-parse", "HEAD").stdout.strip()
        return passed, {
            "gate_id": gate["id"], "head": head, "result_sha256": str(len(gate_calls)),
            "recorded_at": orch.iso_now(), "exit_code": 0 if passed else 1,
        }, blocker
    monkeypatch.setattr(orch, "run_gate_command", fake_gate)
    ctx = orch.RunContext(
        repo=repo, target="TASK-SIM-011", report_base=tmp_path / "reports",
        verbose=False, show_tail=0, heartbeat_seconds=0,
    )
    result = orch.run_task("TASK-SIM-011", repo, _model_policy(), ctx=ctx, max_fix_cycles=1)
    assert result["status"] == "ACCEPTED"
    assert gate_calls == ["G0", "G0", "G0"]
    assert roles.count("gate_fix") == 2
    checkpoint = ctx.run_dir.parent / "resume_TASK-SIM-011.json"
    state = json.loads(checkpoint.read_text(encoding="utf-8"))
    assert state["phase"] == "accepted"
    assert state["finalization"]["binding_verified"] is True
    assert state["literal_validation"]["results"][0]["exit_code"] == 0


def test_integrated_legacy_lifecycle_skips_staged_phases(tmp_path, monkeypatch):
    repo = tmp_path / "legacy"
    repo.mkdir()
    _prepare_lifecycle_repo(repo, staged=False)
    roles = []
    monkeypatch.setattr(orch, "run_stage", _fake_stage_runner(roles))
    ctx = orch.RunContext(
        repo=repo, target="TASK-SIM-011", report_base=tmp_path / "legacy-reports",
        verbose=False, show_tail=0, heartbeat_seconds=0,
    )
    result = orch.run_task("TASK-SIM-011", repo, _model_policy(), ctx=ctx, max_fix_cycles=1)
    assert result["status"] == "ACCEPTED"
    assert roles == ["implementation", "review"]
    checkpoint = ctx.run_dir.parent / "resume_TASK-SIM-011.json"
    state = json.loads(checkpoint.read_text(encoding="utf-8"))
    assert state["qualification_profile"] is None
    assert state["finalization"]["source_commit"] is None


def test_merge_run_stage_metrics_is_idempotent_for_same_run_id():
    state = orch.upgrade_checkpoint_state({"schema_version": 2}, staged=True)
    record = orch.StageRunRecord(
        task_id="TASK-SIM-011", role="gate_fix", model="m", reasoning_effort="medium",
        started_at="now", tokens_reported=10,
    )
    assert orch.merge_run_stage_metrics(state, [record], run_id="run-1") is True
    assert orch.merge_run_stage_metrics(state, [record], run_id="run-1") is False
    assert state["aggregate"]["codex_calls"] == 1
    assert state["aggregate"]["gate_fix_calls"] == 1


def test_staged_review_fix_invalidates_proof_and_reruns_gate_pipeline(tmp_path, monkeypatch):
    repo = tmp_path / "review-fix"
    repo.mkdir()
    _prepare_lifecycle_repo(repo, staged=True)
    roles = []
    review_calls = {"count": 0}

    def fake_stage(prompt, repo_path, config, *, ctx, task_id, role):
        roles.append(role)
        if role == "implementation":
            return orch.StageResult(task_id, "implementation", "COMPLETE", {
                "task_id": task_id, "stage": "implementation", "status": "COMPLETE", "workflow_complete": True
            })
        if role == "review":
            review_calls["count"] += 1
            return orch.StageResult(task_id, "review", "REJECT", {
                "task_id": task_id, "stage": "review", "status": "REJECT", "workflow_complete": True
            })
        if role == "fix":
            (repo_path / "scripts" / "app.py").write_text("VALUE = 2\n", encoding="utf-8")
            return orch.StageResult(task_id, "fix", "READY_FOR_RE_REVIEW", {
                "task_id": task_id, "stage": "fix", "status": "READY_FOR_RE_REVIEW", "workflow_complete": True
            })
        if role == "rereview":
            return orch.StageResult(task_id, "review", "ACCEPT", {
                "task_id": task_id, "stage": "review", "status": "ACCEPT", "workflow_complete": True
            })
        raise AssertionError(f"unexpected role {role}")

    monkeypatch.setattr(orch, "run_stage", fake_stage)
    gate_calls = []
    def pass_gate(repo_path, gate):
        gate_calls.append(gate["id"])
        head = orch.run_git(repo_path, "rev-parse", "HEAD").stdout.strip()
        return True, {
            "gate_id": gate["id"], "head": head, "result_sha256": str(len(gate_calls)),
            "recorded_at": orch.iso_now(), "exit_code": 0,
        }, None
    monkeypatch.setattr(orch, "run_gate_command", pass_gate)
    ctx = orch.RunContext(
        repo=repo, target="TASK-SIM-011", report_base=tmp_path / "review-fix-reports",
        verbose=False, show_tail=0, heartbeat_seconds=0,
    )
    result = orch.run_task("TASK-SIM-011", repo, _model_policy(), ctx=ctx, max_fix_cycles=1)
    assert result["status"] == "ACCEPTED"
    assert gate_calls == ["G0", "G0"]
    assert roles == ["implementation", "review", "fix", "rereview"]
    checkpoint = ctx.run_dir.parent / "resume_TASK-SIM-011.json"
    state = json.loads(checkpoint.read_text(encoding="utf-8"))
    assert state["gate_state"]["current_gate_index"] == 1
    assert state["gate_state"]["attempt_id"] >= 2
    assert state["finalization"]["binding_verified"] is True


def test_forced_staged_resume_head_mismatch_restarts_from_gate_resolution(tmp_path, monkeypatch):
    import subprocess
    repo = tmp_path / "forced-resume"
    repo.mkdir()
    _prepare_lifecycle_repo(repo, staged=True)
    base = orch.run_git(repo, "rev-parse", "HEAD").stdout.strip()
    contract = orch.load_task_orchestrator_contract(repo, "TASK-SIM-011")
    assert contract is not None
    protected = orch.snapshot_protected_artifacts(repo, contract.protected_paths, authority_commit=base)
    assessment = orch.TaskAssessment(
        task_id="TASK-SIM-011", task_class="GREEN", score=0,
        reasons=("explicit",), task_path="tasks/TASK-SIM-011.md", explicit_override=True,
    )
    resume_state = orch.upgrade_checkpoint_state({
        "task_id": "TASK-SIM-011", "repo": str(repo), "branch": orch.current_branch(repo),
        "initial_head": base, "current_head": base, "phase": "literal_validation",
        "status": "RUNNING", "task_assessment": orch.asdict(assessment),
        "effective_task_class": "GREEN", "commits": [], "fix_cycles_used": 0,
        "max_fix_cycles": 1, "protected_artifacts": protected,
        "review_return_phase": "review",
    }, staged=True)
    resume_state["gate_state"]["current_gate_index"] = 1
    resume_state["gate_state"]["passed_gates"] = {"G0": {"status": "PASS"}}
    resume_state["finalization"]["source_commit"] = base
    resume_state["finalization"]["binding_verified"] = True
    resume_state["literal_validation"]["results"] = [{"exit_code": 0}]

    (repo / "scripts" / "app.py").write_text("VALUE = 9\n", encoding="utf-8")
    subprocess.run(["git", "add", "scripts/app.py"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-qm", "manual verified change"], cwd=repo, check=True)
    new_head = orch.run_git(repo, "rev-parse", "HEAD").stdout.strip()
    assert new_head != base

    roles = []
    monkeypatch.setattr(orch, "run_stage", _fake_stage_runner(roles))
    gate_calls = []
    def pass_gate(repo_path, gate):
        gate_calls.append(gate["id"])
        head = orch.run_git(repo_path, "rev-parse", "HEAD").stdout.strip()
        return True, {
            "gate_id": gate["id"], "head": head, "result_sha256": "forced",
            "recorded_at": orch.iso_now(), "exit_code": 0,
        }, None
    monkeypatch.setattr(orch, "run_gate_command", pass_gate)
    ctx = orch.RunContext(
        repo=repo, target="TASK-SIM-011", report_base=tmp_path / "forced-reports",
        verbose=False, show_tail=0, heartbeat_seconds=0,
    )
    result = orch.run_task(
        "TASK-SIM-011", repo, _model_policy(), ctx=ctx,
        max_fix_cycles=1, resume_state=resume_state, resume_force=True,
    )
    assert result["status"] == "ACCEPTED"
    assert gate_calls == ["G0"]
    assert roles == ["review"]
    checkpoint = ctx.run_dir.parent / "resume_TASK-SIM-011.json"
    state = json.loads(checkpoint.read_text(encoding="utf-8"))
    assert state["finalization"]["source_commit"] == new_head
    assert state["finalization"]["binding_verified"] is True


def test_resume_cli_exposes_new_host_owned_phases():
    import subprocess, sys
    proc = subprocess.run(
        [sys.executable, str(MODULE_PATH), "resume", "--help"],
        text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
    )
    assert proc.returncode == 0
    assert "gate_resolution" in proc.stdout
    assert "finalization" in proc.stdout
    assert "literal_validation" in proc.stdout


def test_new_staged_failure_statuses_have_specific_next_actions():
    cases = {
        "GATE_BLOCKED": "RESOLVE_GATE_BLOCKER",
        "ARCHITECTURE_REVIEW_REQUIRED": "REVIEW_GATE_ARCHITECTURE",
        "GATE_FIX_NOT_READY": "RESOLVE_GATE_FIX_BLOCKER",
        "IMMUTABLE_FINALIZATION_FAILED": "REPAIR_IMMUTABLE_FINALIZATION",
        "CANONICAL_RUN_FAILED": "REPAIR_CANONICAL_RUN",
        "LITERAL_VALIDATION_FAILED": "REPAIR_LITERAL_VALIDATION",
        "LITERAL_VALIDATION_BLOCKED": "REPAIR_LITERAL_VALIDATION",
    }
    for status, expected in cases.items():
        action, _ = orch.derive_next_action({"status": status}, [])
        assert action == expected


def test_source_finalization_allows_declared_non_source_finalization_paths_without_hashing_them(tmp_path):
    _init_git_repo(tmp_path)
    history = tmp_path / "docs" / "task_history" / "TASK-SIM-011"
    history.mkdir(parents=True)
    (history / "01_diagnosis.md").write_text("resolved\n", encoding="utf-8")
    (tmp_path / "scripts" / "app.py").write_text("x = 8\n", encoding="utf-8")
    commit, hashes = orch.commit_source_finalization(
        tmp_path,
        task_id="TASK-SIM-011",
        source_paths=("scripts/app.py",),
        finalization_paths=("scripts/app.py", "docs/task_history/TASK-SIM-011"),
    )
    assert "scripts/app.py" in hashes
    assert "docs/task_history/TASK-SIM-011/01_diagnosis.md" not in hashes
    assert orch.run_git(tmp_path, "show", f"{commit}:docs/task_history/TASK-SIM-011/01_diagnosis.md").stdout == "resolved\n"


def _make_finalization_record(repo: Path):
    commit = orch.run_git(repo, "rev-parse", "HEAD").stdout.strip()
    results = repo / "results"
    results.mkdir(exist_ok=True)
    evidence = results / "evidence.json"
    evidence.write_text(json.dumps({"source_git_sha": commit, "source_hashes": {}}) + "\n", encoding="utf-8")
    binding = orch.verify_canonical_evidence_bindings(repo, commit, ("results/evidence.json",))
    return {
        "source_commit": commit,
        "source_hashes": {"scripts/app.py": orch.git_path_sha256(repo, commit, "scripts/app.py")},
        "canonical_results": [],
        "binding_verified": True,
        "binding": binding,
    }


def test_finalization_authority_guard_blocks_source_mutation_before_review(tmp_path):
    _init_git_repo(tmp_path)
    finalization = _make_finalization_record(tmp_path)
    (tmp_path / "scripts" / "app.py").write_text("x = 99\n", encoding="utf-8")
    import pytest
    with pytest.raises(orch.OrchestratorError, match="FINALIZATION_AUTHORITY_VIOLATION"):
        orch.assert_finalization_authority_unchanged(
            tmp_path,
            finalization=finalization,
            source_paths=("scripts/app.py",),
            evidence_paths=("results/evidence.json",),
            literal_results=(),
        )


def test_finalization_authority_guard_blocks_evidence_mutation_before_review(tmp_path):
    _init_git_repo(tmp_path)
    finalization = _make_finalization_record(tmp_path)
    evidence = tmp_path / "results" / "evidence.json"
    payload = json.loads(evidence.read_text(encoding="utf-8"))
    payload["tampered"] = True
    evidence.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    import pytest
    with pytest.raises(orch.OrchestratorError, match="FINALIZATION_AUTHORITY_VIOLATION"):
        orch.assert_finalization_authority_unchanged(
            tmp_path,
            finalization=finalization,
            source_paths=("scripts/app.py",),
            evidence_paths=("results/evidence.json",),
            literal_results=(),
        )
