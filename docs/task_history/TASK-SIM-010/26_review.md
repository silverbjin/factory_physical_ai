# Review — TASK-SIM-010

- Recommendation: REJECT
- Review stage: `S10-G8 INDEPENDENT_REREVIEW`
- Reviewed source candidate: `2179d965b64abac79c068a94363b9a67e9f4739b`
- Reviewed canonical Evidence commit: `f7a135a0bc3d6f9b22fc17f63b838ed17bde0217`
- G6 result: `SIM_OBSERVABILITY_REGRESSION_READY` (canonical claim invalidated by the findings below)
- G7 result: repeatability reproduced for serialized core semantics and corrected full-regression facts
- Failed Gates: Contract, Invariants, Tests, Evidence (`S10-G4`, `S10-G6`, `S10-G8`)
- Validation: focused `51 passed`; candidate `396` collected / `4 failed, 392 passed`; baseline `341` collected / `4 failed, 337 passed`; complete failed-node sets and non-empty stable signatures exactly equal; `PASS_PROVEN_PREEXISTING`
- Evidence: SHA256 `46a13b9e4b7030564df5275f3a06b9b6bcdcf536e7e6d52f079db3e03df9b978`; requirement classification `53 / 21 / 32 / 0`; canonical READY is not acceptance-safe because physics/applicability enforcement remains fail-open
- Acceptance recorded: NO

## Independent Verification

- Q01 Acceptance와 Evidence를 pinned immutable Git objects에서 재구성했고 Evidence SHA256 `dbd2fc20f6072f8889466fff29b80ec874d105b37c5633e909c633facdb2eb6a`를 확인했다.
- candidate/baseline을 각각 clean detached worktree에서 qualified Python과 동일한 full-suite command로 재실행했다.
- candidate-only collection `55`개가 `tests/test_simulation_observability_regression.py`의 `51`개와 `scripts/codex/test_run_task_orchestrator.py`의 `4`개임을 확인했다.
- serialized canonical core를 fresh read-only aggregation과 비교해 semantic equivalence를 확인했다.
- adversarial in-memory probes로 nested retry/reconciliation/lifecycle, provenance, `NOT_APPLICABLE` source enforcement를 검증했다.
- `git diff --check`를 실행했고 history 기록 전 worktree가 clean임을 확인했다.

## Blocking Findings

### SIM010-G8R-001 — BLOCKER

- Requirement / Contract: `TASK-SIM-010.md` §14.9, R7, S10-G4; prior `SIM010-G8-001`
- File / Symbol: `src/simulation_runtime/observability_regression.py::_q01_physics_rows`, `validate_q01_chain`
- Issue: top-level decision/result/status/outcome 비교는 수행하지만 nested retry/reconciliation/lifecycle/state-invariant semantics를 historical oracle과 fail-closed로 비교하지 않는다. `reconciliation_completed=false`, `logical_side_effect_count=2`, reconciliation 삭제, contradictory lifecycle mutation이 모두 수용됐고 arbitrary non-empty provenance mappings도 physics row로 통과했다.
- Why it blocks acceptance: 상충하거나 불완전한 qualification observation이 `physics_semantic_regression = PASS`와 canonical READY를 유지할 수 있다.
- Recommended remediation: historical scenario의 required nested semantics와 exact provenance/applicability claims를 normalized oracle에 보존하고 field별 비교 및 negative tests를 추가한다.

### SIM010-G8R-002 — HIGH

- Requirement / Contract: `TASK-SIM-010.md` §14.6; prior `SIM010-G8-003`
- File / Symbol: `src/simulation_runtime/observability_regression.py::_validate_q01_applicability`
- Issue: `NOT_APPLICABLE` justification과 execution-state booleans는 검사하지만 observation source를 요구하지 않는다. accepted N/A subject에서 `timing.simulation_time_source`를 제거한 mutation이 `validate_q01_chain`을 통과했다.
- Why it blocks acceptance: source가 없는 N/A 주장이 physics/timing measurement 부재를 정당화할 수 있어 applicability gate가 완전히 fail-closed가 아니다.
- Recommended remediation: frozen N/A source/justification contract를 정확히 검증하고 missing/wrong source negative tests를 추가한다.

```yaml
acceptance_handoff:
  schema_version: review_acceptance_handoff_v1
  task_id: TASK-SIM-010
  review_decision: REJECT
  reviewed_commit: 2179d965b64abac79c068a94363b9a67e9f4739b
  task_specific_decision: SIM_OBSERVABILITY_REGRESSION_READY

  task_spec:
    path: tasks/TASK-SIM-010.md
    sha256: f66dd62459de55feb9b76d5c1eec5e45c28181ad9840079880d40429d03fff3d

  evidence:
    required: true
    path: results/simulation/SIM-010_observability_regression.json
    sha256: 46a13b9e4b7030564df5275f3a06b9b6bcdcf536e7e6d52f079db3e03df9b978

  supporting_artifacts:
    - path: docs/simulation/simulation_observability_regression_v1.md
      sha256: 8bb6347fe07aae83cc4e9b2e59f866353ded08dc089851874fc844021bf6b9d9
  acceptance_recording_eligible: false
  blocking_reason: Residual fail-open Q01 physics semantics and NOT_APPLICABLE source validation.
```

Final S10-G8 decision: REJECT
