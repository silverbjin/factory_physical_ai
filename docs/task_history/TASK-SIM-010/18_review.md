# Review — TASK-SIM-010

- Recommendation: REJECT
- Failed Gates: Contract, Invariants, Tests, Evidence (`S10-G4`, `S10-G6`, `S10-G8`)
- Validation: focused `38 passed`; 독립 candidate/baseline full regression은 동일 4-node/non-empty-signature로 `PROVEN_PREEXISTING`
- Evidence: `results/simulation/SIM-010_observability_regression.json` SHA256 `40acf5e3e7d85a86be0d9ddc7b43126474724d5df84c2db243384a7c80460e9d`; `SIM_OBSERVABILITY_REGRESSION_READY` 주장은 아래 findings 때문에 무효

## Blocking Findings

### SIM010-G8-001 — BLOCKER

- Requirement / Contract: `TASK-SIM-010.md` §14.9, R7, S10-G4
- File / Symbol: `src/simulation_runtime/observability_regression.py::_q01_physics_rows`
- Issue: historical oracle와 Q01 observation의 decision/status/outcome, lifecycle, retry/reconciliation, invariants/tolerances, provenance, applicability를 비교하지 않는다. profile 및 문자열 존재만 확인한 뒤 `scenario_pass = True`를 합성한다. 독립 mutation probe에서 `SIM009-NAV-ABORTED`를 `CONTRADICTORY_DECISION/success/completed`로 바꿔도 failure 없이 physics row로 수용됐다.
- Why it blocks acceptance: 상충하는 Q01 관측도 `physics_semantic_regression = PASS`와 READY를 만들 수 있어 G4/G6 Evidence가 fail-closed가 아니다.
- Recommended remediation: 각 frozen subject에 대해 historical oracle과 qualification observation의 모든 §14.9 필드를 명시적으로 비교하고 mismatch negative tests를 추가한다.

### SIM010-G8-002 — BLOCKER

- Requirement / Contract: `TASK-SIM-010.md` §14.5, G0; immutable predecessor tuple validation
- File / Symbol: `src/simulation_runtime/observability_regression.py:validate_q01_chain`, `resolve_q01_qualification`
- Issue: SIM-008/SIM-009 predecessor Acceptance를 pinned Git object가 아니라 mutable worktree `results/reviews/<TASK>_acceptance.json`에서 읽는다.
- Why it blocks acceptance: Q01 subject-to-predecessor 결합이 immutable Acceptance object에서 독립 재구성되지 않아 명시적으로 금지된 mutable-worktree association이다.
- Recommended remediation: 각 predecessor Acceptance recording commit/path를 고정하고 Acceptance→accepted commit→Evidence blob/hash→expected result 전체를 immutable Git object로 해석한다.

### SIM010-G8-003 — HIGH

- Requirement / Contract: `TASK-SIM-010.md` §14.4, §14.6, §14.7; fail-closed scope/applicability/duplicate authority
- File / Symbol: `src/simulation_runtime/observability_regression.py:validate_q01_chain`, `_validate_q01_applicability`; `tests/test_simulation_observability_regression.py`
- Issue: supporting authority claim allowlist와 predecessor tuple을 검증하지 않고, `NOT_APPLICABLE` justification/source 및 scenario execution identity uniqueness도 강제하지 않는다. 독립 probes에서 undeclared `request_id` claim, zero support Evidence hash, 누락된 N/A justification이 모두 수용됐다. 해당 negative tests도 없다.
- Why it blocks acceptance: 지원 authority가 run-local claim을 공급하거나 잘못된 binding/applicability가 READY에 진입할 수 있다.
- Recommended remediation: exact claim allowlists와 immutable support tuple, applicability justification/source, qualification scenario execution identity uniqueness를 검증하고 각각 mutation negative tests를 추가한다.

```yaml
acceptance_handoff:
  schema_version: review_acceptance_handoff_v1
  task_id: TASK-SIM-010
  review_decision: REJECT
  reviewed_commit: 2ec859845628992b02686a6d8bcdbcb77985a5a2
  task_specific_decision: SIM_OBSERVABILITY_REGRESSION_READY

  task_spec:
    path: tasks/TASK-SIM-010.md
    sha256: f66dd62459de55feb9b76d5c1eec5e45c28181ad9840079880d40429d03fff3d

  evidence:
    required: true
    path: results/simulation/SIM-010_observability_regression.json
    sha256: 40acf5e3e7d85a86be0d9ddc7b43126474724d5df84c2db243384a7c80460e9d

  supporting_artifacts:
    - path: docs/simulation/simulation_observability_regression_v1.md
      sha256: c0a35231dfa223ee97b6628762c555d986039d12bd0a3436338ce5cda1de69b5
  acceptance_recording_eligible: false
  blocking_reason: S10-G4 semantic comparison and immutable authority validation are fail-open
```

review_stage:
S10-G8 INDEPENDENT_REVIEW

S10_G8:
REJECT

reviewed_source_candidate:
2ec859845628992b02686a6d8bcdbcb77985a5a2
reviewed_canonical_evidence:
results/simulation/SIM-010_observability_regression.json @ 40acf5e3e7d85a86be0d9ddc7b43126474724d5df84c2db243384a7c80460e9d
reviewed_evidence_commit:
0c010f761e344df7e15a127c495a78828dd4208e

q01_authority_verified:
YES
historical_q01_separation_verified:
YES
exact_subject_set_verified:
YES
claim_scope_verified:
NO
predecessor_binding_verified:
NO
applicability_verified:
NO
duplicate_authority_prevention_verified:
NO
deterministic_replay_verified:
YES
physics_semantic_regression_verified:
NO
qualified_environment_verified:
YES
source_isolation_verified:
YES
full_regression_verified:
YES
proven_preexisting_verified:
YES
canonical_evidence_integrity_verified:
NO
repeatability_verified:
YES
protected_scope_verified:
YES

blocking_finding_ids:
SIM010-G8-001, SIM010-G8-002, SIM010-G8-003
review_decision:
REJECT

acceptance_recorded:
NO
next_action:
RESOLVE_REVIEW_FINDINGS_BEFORE_ACCEPTANCE
