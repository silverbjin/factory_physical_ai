# Review — TASK-SIM-Q01-MIN

- Recommendation: REJECT
- Failed Gates: Scope, Requirements, Contract, Invariants, Tests, Evidence
- Validation: `pytest -q tests/test_simulation_provenance_qualification.py` → 28 passed, 2 skipped; `git diff --check` → PASS
- Evidence: `results/simulation/SIM-Q01_provenance_qualification.json` MISSING

## Blocking Findings

### Q01MIN-EVIDENCE-001 — BLOCKER

- Requirement / Contract: TASK Sections 10–12 completion gate
- File / Symbol: `results/simulation/SIM-Q01_provenance_qualification.json`
- Issue: 11개 신규 operation subject의 실행 및 canonical machine Evidence가 생성되지 않음.
- Why it blocks acceptance: 실제 run-local provenance와 task-specific decision을 독립적으로 검증할 수 없음.
- Recommended remediation: 1개 SIM-008과 10개 SIM-009 subject를 실행하여 canonical Evidence를 생성하고 검증할 것.

### Q01MIN-APPLICABILITY-002 — HIGH

- Requirement / Contract: `configs/simulation/min_q01_scope.json#applicability_policy`
- File / Symbol: `collect_sim008_execution_result`, `collect_sim009_execution_result`, `validate_subject`
- Issue: physics가 실행된 subject의 `physics_measurement`를 `OPTIONAL`로 표시하고 REQUIRED field 존재를 검증하지 않음.
- Why it blocks acceptance: physics measurement가 없는 subject도 READY로 집계될 수 있음.
- Recommended remediation: physics 실행 경로를 `REQUIRED`로 분류하고 실제 measurement를 fail-closed 검증하며 pre-physics만 `NOT_APPLICABLE`로 허용할 것.

### Q01MIN-SIM009-SEMANTICS-003 — HIGH

- Requirement / Contract: TASK Section 8 applicable retry/recovery/reconciliation/Verification semantics
- File / Symbol: `run_sim009_qualification`, `collect_sim009_execution_result`
- Issue: `SIM009-NAV-TIMEOUT-RETRY`, `SIM009-VLA-TIMEOUT`, `SIM009-VLA-UNKNOWN`의 reconciliation/retry 구조를 버리고 decision/result/status만 Evidence outcome으로 보존함.
- Why it blocks acceptance: accepted outcome 비교 외의 필수 실행 semantics를 신규 run에서 증명하지 못함.
- Recommended remediation: 해당 scenario의 retry authorization/result와 reconciliation identity/outcome을 run-local Evidence에 보존하고 테스트할 것.

### Q01MIN-CONTRACTB-004 — HIGH

- Requirement / Contract: TASK Section 3 frozen Contract-B bindings
- File / Symbol: `resolve_predecessor_binding`, `scripts/run_simulation_provenance_qualification.py:FROZEN`
- Issue: resolver가 worktree Acceptance의 commit과 계산한 blob hash를 frozen commit/hash 표 및 task-specific result와 비교하지 않음.
- Why it blocks acceptance: 변경된 Acceptance가 다른 Git object로 authority를 재지정해도 Contract B가 통과할 수 있음.
- Recommended remediation: 5개 predecessor의 exact accepted commit, Evidence path, SHA256, task-specific result를 frozen contract과 비교하고 mismatch를 차단할 것.

```yaml
acceptance_handoff:
  schema_version: review_acceptance_handoff_v1
  task_id: TASK-SIM-Q01-MIN
  review_decision: REJECT
  reviewed_commit: fb383e6ccbe11d9654ab62f392e1dd8be4603973
  task_specific_decision: null

  task_spec:
    path: tasks/TASK-SIM-Q01-MIN.md
    sha256: 6f1a068febd83a7bd2dde775603d1beca644dfc9c65c06efc41250a643047203

  evidence:
    required: true
    path: results/simulation/SIM-Q01_provenance_qualification.json
    sha256: null

  supporting_artifacts: []

  acceptance_recording_eligible: false
  blocking_reason: Canonical Evidence is missing and required applicability, SIM-009 semantics, and frozen Contract-B checks are incomplete.
```
