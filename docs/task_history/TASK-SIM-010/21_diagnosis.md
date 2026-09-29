# Diagnosis — TASK-SIM-010

- Result: RESOLVED
- Status: RESOLVED
- Trigger: 두 번째 independent Review의 `SIM010-RR-001`, `SIM010-RR-002`
- Triggering status: `REJECTED_AFTER_REVIEW`
- Diagnosis tier/model: targeted read-only technical diagnosis / GPT-5.6 Sol, high reasoning

## Trigger

`build_regression_evidence()`가 유효한 Q01 binding 하나로 모든
`required_run_failures`를 제거했고, 최신 Fix가 commit되기 전에 canonical
aggregation과 REREVIEW가 실행되었다. 최신 orchestrator commit은
`2a800f01f3683cf3c2e8159e381e86bdc7822c74`이다.

## Requirement / Contract

- R2–R5와 R10은 requirement-scoped fact가 실제 authority로 증명되어야 하며
  누락을 전역 Q01 존재 여부로 해제할 수 없다.
- §14.2–§14.6과 `13_diagnosis.md`는 SIM-004/SIM-005/SIM-007을
  `immutable_accepted_authority` support로, 정확히 11개 SIM-008/SIM-009
  qualification subject를 `run_local` operation authority로 분리한다.
- §14.10은 immutable candidate의 raw full-suite FAIL도 완전한 failed-node set과
  non-empty stable signature가 baseline과 동일하면 `PROVEN_PREEXISTING`으로
  S10-G5를 통과할 수 있게 한다. 따라서 `result = FAIL`과 READY의 병존 자체는
  blocker가 아니지만, tested candidate가 실제 Fix commit이어야 하고 R11 summary는
  완전해야 한다.
- §14.12는 immutable candidate를 고정한 뒤 S10-G0부터 S10-G8까지 순서대로
  수행하도록 요구한다.

## Authoritative Source

- `tasks/TASK-SIM-010.md`, 특히 R2–R5, R10–R12, EC6, §14.2–§14.12
- `docs/task_history/TASK-SIM-010/13_diagnosis.md`
- `docs/task_history/TASK-SIM-010/18_review.md`
- `docs/task_history/TASK-SIM-010/19_fix.md`
- `docs/task_history/TASK-SIM-010/20_review.md`
- `src/simulation_runtime/observability_regression.py`
- `scripts/run_simulation_observability_regression.py`
- `tests/test_simulation_observability_regression.py`
- `results/simulation/SIM-010_observability_regression.json`
- `docs/simulation/simulation_observability_regression_v1.md`
- immutable Q01 Acceptance/Evidence objects at
  `a1f1539c27f61fb2ce52aed33ceaf1bfe343912c` and
  `b55bc4fc2435e83c3761457b92d9e14892e39435`; recomputed Q01 Evidence SHA256
  `dbd2fc20f6072f8889466fff29b80ec874d105b37c5633e909c633facdb2eb6a`
- latest orchestrator run report/checkpoint under
  `/home/jinho/.local/state/codex-task-orchestrator/factory_physical_ai_sim_010/20260929-172858_TASK-SIM-010/`
- immutable Git objects `0dc8e71c3b2aec56557fdfb54de83d3e446cd0a7` and
  `2a800f01f3683cf3c2e8159e381e86bdc7822c74`

## Root Cause

1. `observability_regression.py:1176-1189` computes per-source validation failures,
   then replaces the entire set with `[]` whenever `q01 is not None`. This loses the
   distinction between historical diagnostic gaps, explicitly Q01-qualified facts,
   and genuinely unproved facts.
2. The recovery orchestrator transitions `fix -> rereview -> commit_fix_rereview`.
   The Fix worker therefore generated Evidence while HEAD was still `0dc8e71...` and
   source/tests were modified only in the worktree. The runner built aggregation from
   that worktree but detached and tested HEAD, then labeled the artifact with HEAD.
   REREVIEW inspected the uncommitted Fix worktree, and only after REJECT did the
   orchestrator commit it as `2a800f01...`.

## Fault Domain

- `SIM010_REQUIREMENT_SCOPED_AUTHORITY_GATING_DEFECT`
- `SIM010_IMMUTABLE_CANDIDATE_LIFECYCLE_DEFECT`
- external/process limitation: current orchestrator Fix/Rereview ordering is unsafe
  for a task whose gates and Evidence must bind an immutable post-Fix candidate.

## RR-001 Requirement-Scoped Authority Analysis

Current Q01 is sufficient only with a requirement-scoped correction:

```text
CURRENT_Q01_SUFFICIENT_WITH_REQUIREMENT_SCOPED_FIX
```

SIM-004/SIM-005/SIM-007 deficiencies remain visible historical truth and are not
Q01-repaired. Under the existing §14 authority split and `13_diagnosis.md`, those
sources are supporting authority rather than frozen operation subjects, so their
historical run-local deficiencies are diagnostic-only after the downstream
requirement is independently satisfied. SIM-008/SIM-009 deficiencies are satisfied
only by exact subject/scenario mappings to separately namespaced Q01 `run_local`
observations. No `STILL_BLOCKING` failure remains in current accepted authority.

## Indexed Failure Classification

The table groups multiple failure codes on the same indexed run; all 53 individual
reported failures are represented. `NO` in `does_Q01_prove_the_same_required_fact`
means the historical deficiency remains unaltered.

| source_task | source_scenario_or_run | failed_requirement | missing_field_or_claim | historical_authority_status | possible_Q01_or_support_authority | Q01_claim_scope | exact_authorized_claim | does_Q01_prove_the_same_required_fact | may_failure_stop_gating_readiness | reason |
|---|---|---|---|---|---|---|---|---|---|---|
| SIM-004 | RUN[0] `success` | R4 | `MISSING_SIMULATION_TIME` | accepted historical row, incomplete | SIM-004 support binding | `immutable_accepted_authority` | component/version, runtime, world, bridge, runner authority | NO | NO | historical timing is outside the support allowlist; row remains diagnostic and is not a frozen operation subject |
| SIM-004 | RUN[3] `blocked` | R4 | `MISSING_SIMULATION_TIME` | accepted historical row, incomplete | SIM-004 support binding | `immutable_accepted_authority` | component/version, runtime, world, bridge, runner authority | NO | NO | same requirement-scope rule; no historical backfill |
| SIM-004 | RUN[4] `timeout_reconciliation` | R4 | `MISSING_SIMULATION_TIME` | accepted historical row, incomplete | SIM-004 support binding | `immutable_accepted_authority` | component/version, runtime, world, bridge, runner authority | NO | NO | same requirement-scope rule; no historical backfill |
| SIM-005 | RUN[0] `mujoco-place-nominal` | R2 | `MISSING_TRACE_ID`; `INCOMPLETE_CORRELATION_IDENTITY` | accepted historical row, incomplete | SIM-005 support binding | `immutable_accepted_authority` | MuJoCo version, model/scene/config, version-wide seed/timestep, accepted initial state | NO | NO | run-local identity is forbidden to support authority; row remains diagnostic and is not a frozen operation subject |
| SIM-005 | RUN[1] `mujoco-grasp-miss` | R2 | `MISSING_TRACE_ID`; `INCOMPLETE_CORRELATION_IDENTITY` | accepted historical row, incomplete | SIM-005 support binding | `immutable_accepted_authority` | same SIM-005 support allowlist | NO | NO | same requirement-scope rule; no historical backfill |
| SIM-005 | RUN[2] `mujoco-contact-loss` | R2 | `MISSING_TRACE_ID`; `INCOMPLETE_CORRELATION_IDENTITY` | accepted historical row, incomplete | SIM-005 support binding | `immutable_accepted_authority` | same SIM-005 support allowlist | NO | NO | same requirement-scope rule; no historical backfill |
| SIM-005 | RUN[3] `mujoco-workspace-limit` | R2 | `MISSING_TRACE_ID`; `INCOMPLETE_CORRELATION_IDENTITY` | accepted historical row, incomplete | SIM-005 support binding | `immutable_accepted_authority` | same SIM-005 support allowlist | NO | NO | same requirement-scope rule; no historical backfill |
| SIM-005 | RUN[4] `mujoco-invalid-observation` | R2 | `MISSING_TRACE_ID`; `INCOMPLETE_CORRELATION_IDENTITY` | accepted historical row, incomplete | SIM-005 support binding | `immutable_accepted_authority` | same SIM-005 support allowlist | NO | NO | same requirement-scope rule; no historical backfill |
| SIM-005 | RUN[5] `mujoco-timeout` | R2 | `MISSING_TRACE_ID`; `INCOMPLETE_CORRELATION_IDENTITY` | accepted historical row, incomplete | SIM-005 support binding | `immutable_accepted_authority` | same SIM-005 support allowlist | NO | NO | same requirement-scope rule; no historical backfill |
| SIM-005 | RUN[6] `mujoco-unknown` | R2 | `MISSING_TRACE_ID`; `INCOMPLETE_CORRELATION_IDENTITY` | accepted historical row, incomplete | SIM-005 support binding | `immutable_accepted_authority` | same SIM-005 support allowlist | NO | NO | same requirement-scope rule; no historical backfill |
| SIM-007 | RUN[0] `deterministic` | R3 | `MISSING_SOURCE_CONFIG_HASHES` | accepted historical aggregate, incomplete | SIM-007 support binding | `immutable_accepted_authority` | profile identity, profile source/config authority, accepted aggregate outcome | NO | NO | support claim does not create missing per-run hashes; aggregate remains diagnostic and is not a frozen operation subject |
| SIM-007 | RUN[1] `navigation_physics` | R3 | `MISSING_SOURCE_CONFIG_HASHES` | accepted historical aggregate, incomplete | SIM-007 support binding | `immutable_accepted_authority` | same SIM-007 support allowlist | NO | NO | same requirement-scope rule; no historical backfill |
| SIM-007 | RUN[2] `manipulation_physics` | R3 | `MISSING_SOURCE_CONFIG_HASHES` | accepted historical aggregate, incomplete | SIM-007 support binding | `immutable_accepted_authority` | same SIM-007 support allowlist | NO | NO | same requirement-scope rule; no historical backfill |
| SIM-007 | RUN[3] `system` | R3 | `MISSING_SOURCE_CONFIG_HASHES` | accepted historical aggregate, incomplete | SIM-007 support binding | `immutable_accepted_authority` | same SIM-007 support allowlist | NO | NO | same requirement-scope rule; no historical backfill |
| SIM-008 | RUN[0] `SIM_NORMAL_BRAKE_ECU_LINE_B` | R3/R4 | `MISSING_BRIDGE_SHA256`; `MISSING_LAUNCH_SHA256` | accepted historical oracle, incomplete | `q01-sim008-normal-system-authority` | `run_local` | bridge config `b00fdf7c1c7b9b3a83ea211d88a05f7e6477b04d27d8fd5f9cded0733bce2d3d`; launch/run config `1da47e9dd0a174a2124ee6493b534d295d0b93be77b5446c8661fd863888beb4` | YES | NO | explicit Q01 subject proves the same downstream config-provenance fact without altering the historical row |
| SIM-009 | RUN[3] `SIM009-NAV-BLOCKED` | R3/R4 | `MISSING_SOURCE_HASH:run_config_sha256`; `MISSING_WORLD_MODEL_SHA256`; `MISSING_SIMULATION_TIME` | accepted historical oracle, incomplete | `q01-sim009-SIM009-NAV-BLOCKED` | `run_local` | run config `4df8805ce573247084b38f8ea98da4893e089e4e89a25466c1f86d7196df9002`, world `c26bf7270026bce976abf4bce7f6b2a188885396281c2139970461db01486959`, structured `38.808s` | YES | NO | exact subject/scenario qualification supplies current run-local facts |
| SIM-009 | RUN[4] `SIM009-NAV-ABORTED` | R3/R4 | same three claims | accepted historical oracle, incomplete | `q01-sim009-SIM009-NAV-ABORTED` | `run_local` | run config `4df8805ce573247084b38f8ea98da4893e089e4e89a25466c1f86d7196df9002`, world `c26bf7270026bce976abf4bce7f6b2a188885396281c2139970461db01486959`, structured `39.003s` | YES | NO | exact subject/scenario qualification supplies current run-local facts |
| SIM-009 | RUN[5] `SIM009-NAV-TIMEOUT-RETRY` | R3/R4 | same three claims | accepted historical oracle, incomplete | `q01-sim009-SIM009-NAV-TIMEOUT-RETRY` | `run_local` | run config `4df8805ce573247084b38f8ea98da4893e089e4e89a25466c1f86d7196df9002`, world `c26bf7270026bce976abf4bce7f6b2a188885396281c2139970461db01486959`, structured `40.488s` | YES | NO | retry semantics do not create replay authority; they do supply this subject's run-local provenance |
| SIM-009 | RUN[6] `SIM009-NAV-TF-UNAVAILABLE` | R3/R4 | same three claims | accepted historical oracle, incomplete | `q01-sim009-SIM009-NAV-TF-UNAVAILABLE` | `run_local` | run config `4df8805ce573247084b38f8ea98da4893e089e4e89a25466c1f86d7196df9002`, world `c26bf7270026bce976abf4bce7f6b2a188885396281c2139970461db01486959`, structured `48.804s` | YES | NO | exact subject/scenario qualification supplies current run-local facts |
| SIM-009 | RUN[7] `SIM009-VLA-GRASP-MISS` | R3/R5 | same three claims | accepted historical oracle, incomplete | `q01-sim009-SIM009-VLA-GRASP-MISS` | `run_local` | config `34c0900610d69e5f7500bcf0121490c984a62b20943e89dd3bc7d5c0c87b84a9`, model `21fcb775690b058285480d77c96c788779bd8e7aaced663ba6eeda4691dfd160`, structured `0.8s` | YES | NO | exact subject/scenario qualification supplies current run-local facts |
| SIM-009 | RUN[8] `SIM009-VLA-CONTACT-LOSS` | R3/R5 | same three claims | accepted historical oracle, incomplete | `q01-sim009-SIM009-VLA-CONTACT-LOSS` | `run_local` | config `34c0900610d69e5f7500bcf0121490c984a62b20943e89dd3bc7d5c0c87b84a9`, model `21fcb775690b058285480d77c96c788779bd8e7aaced663ba6eeda4691dfd160`, structured `0.8s` | YES | NO | exact subject/scenario qualification supplies current run-local facts |
| SIM-009 | RUN[9] `SIM009-VLA-WORKSPACE-LIMIT` | R3/R5 | same three claims | accepted historical oracle, incomplete | `q01-sim009-SIM009-VLA-WORKSPACE-LIMIT` | `run_local` | config `34c0900610d69e5f7500bcf0121490c984a62b20943e89dd3bc7d5c0c87b84a9`, model `21fcb775690b058285480d77c96c788779bd8e7aaced663ba6eeda4691dfd160`, plus accepted `NOT_APPLICABLE`, `simulator_started=false`, `physics_started=false` | YES | NO | structured pre-physics state proves timing non-applicability; no synthetic value is used |
| SIM-009 | RUN[10] `SIM009-VLA-TIMEOUT` | R3/R5 | same three claims | accepted historical oracle, incomplete | `q01-sim009-SIM009-VLA-TIMEOUT` | `run_local` | config `34c0900610d69e5f7500bcf0121490c984a62b20943e89dd3bc7d5c0c87b84a9`, model `21fcb775690b058285480d77c96c788779bd8e7aaced663ba6eeda4691dfd160`, plus accepted `NOT_APPLICABLE`, `simulator_started=false`, `physics_started=false` | YES | NO | structured pre-physics state proves timing non-applicability; no synthetic value is used |
| SIM-009 | RUN[11] `SIM009-VLA-AMBIGUOUS` | R3/R5 | same three claims | accepted historical oracle, incomplete | `q01-sim009-SIM009-VLA-AMBIGUOUS` | `run_local` | config `34c0900610d69e5f7500bcf0121490c984a62b20943e89dd3bc7d5c0c87b84a9`, model `21fcb775690b058285480d77c96c788779bd8e7aaced663ba6eeda4691dfd160`, plus accepted `NOT_APPLICABLE`, `simulator_started=false`, `physics_started=false` | YES | NO | structured pre-physics state proves timing non-applicability; no synthetic value is used |
| SIM-009 | RUN[12] `SIM009-VLA-UNKNOWN` | R3/R5 | same three claims | accepted historical oracle, incomplete | `q01-sim009-SIM009-VLA-UNKNOWN` | `run_local` | config `34c0900610d69e5f7500bcf0121490c984a62b20943e89dd3bc7d5c0c87b84a9`, model `21fcb775690b058285480d77c96c788779bd8e7aaced663ba6eeda4691dfd160`, structured `0.8s` | YES | NO | exact subject/scenario qualification supplies current run-local facts |

Classification totals by individual failure code:

```text
remaining_indexed_failure_count = 53
HISTORICAL_DIAGNOSTIC_ONLY_NON_GATING = 21
EXPLICITLY_QUALIFIED_BY_Q01 = 32
STILL_BLOCKING = 0
```

## RR-002 Immutable Candidate Lifecycle Analysis

| Question | Established fact |
|---|---|
| HEAD when FIX started | `0dc8e71c3b2aec56557fdfb54de83d3e446cd0a7` |
| files modified during FIX | source, runner, focused tests, canonical Evidence/report, `19_fix.md`, TASK README |
| source/test state after FIX | modified worktree blobs later committed in `2a800f01...`; focused run reported `44 passed` |
| committed before canonical aggregation | NO |
| detached candidate actually tested | `0dc8e71c3b2aec56557fdfb54de83d3e446cd0a7` |
| Evidence source authority | `0dc8e71c3b2aec56557fdfb54de83d3e446cd0a7` |
| source state inspected by REREVIEW | uncommitted Fix worktree based on `0dc8e71...`; not one immutable commit |
| commit created after REREVIEW | `2a800f01f3683cf3c2e8159e381e86bdc7822c74` |
| one identical immutable implementation across Evidence/regression/review | NO |

The immutable object comparison confirms different source, runner, test, Evidence,
and report blobs between `0dc8e71...` and `2a800f01...`. The run report records
`FIX -> READY_FOR_RE_REVIEW -> REREVIEW -> REJECT -> git_commit`, so this conclusion
does not rely on timestamp proximity.

```text
immutable_candidate_before_evidence: NO
fix_source_committed_before_gates: NO
evidence_used_exact_fix_candidate: NO
rereview_used_exact_fix_candidate: NO
orchestrator_fix_rereview_order_safe: NO
```

The canonical raw full-suite failure currently has the same complete four-node set
and identical non-empty signatures as baseline, so its
`PROVEN_PREEXISTING` classification is structurally permitted by §14.10. It cannot
validate the uncommitted Fix because the detached candidate was stale, and the
artifact also omits the required test-count summary.

## Orchestrator Recovery Safety

The current recovery path is unsafe for this task because commit occurs only after
REREVIEW. Do not repeat the identical orchestrator Fix cycle and do not change
orchestrator source inside TASK-SIM-010. Use this manual bounded sequence:

```text
Fix implementation
-> focused validation
-> COMMIT source/tests
-> freeze immutable candidate SHA
-> S10-G0
-> S10-G1
-> S10-G2
-> S10-G3
-> S10-G4
-> S10-G5
-> S10-G6 canonical Evidence
-> S10-G7 repeatability/finalization
-> independent S10-G8 REREVIEW
```

## Recommended Recovery Mode

```text
MANUAL_BOUNDED_FIX_THEN_MANUAL_REGATE_AND_REREVIEW
```

## Resolution

Q01 authority is sufficient; no task-specification change, architecture decision,
or new qualification task is needed. Replace the blanket Q01 override with explicit
per-failure classification/coverage that preserves historical diagnostics and fails
closed for an unmapped or unproved requirement. Freeze the post-Fix source/test
commit before any canonical gate or Evidence generation.

## Authorized Correction Boundary

- `src/simulation_runtime/observability_regression.py`: requirement-scoped failure
  classification and fail-closed aggregation only.
- `tests/test_simulation_observability_regression.py`: positive and negative tests for
  all three classifications, scope isolation, unmapped facts, and dirty/stale
  candidate rejection.
- `scripts/run_simulation_observability_regression.py`: required; enforce exact clean
  immutable candidate use, bind aggregation/regression/Evidence to it, record the
  required test summary/count, and represent raw FAIL separately from an authorized
  `PROVEN_PREEXISTING` gate result.
- Evidence/report may be regenerated only later at S10-G6 after S10-G0–G5 pass.

## Protected Boundary

Do not change `tasks/TASK-SIM-010.md`, accepted Q01 artifacts, SIM-003 through
SIM-009 accepted artifacts, predecessor history/commits, simulator behavior,
physics implementation, or orchestrator source. Do not expand the frozen 11-subject
set or relabel/coalesce historical and Q01 authority.

## Required Verification

1. Focused tests prove 21 historical deficiencies remain visible and explicitly
   non-gating, 32 deficiencies resolve only through exact Q01 subject mappings, and
   any new/unmapped/mismatched deficiency blocks READY.
2. Commit source/tests/runner before gates and verify a clean worktree plus candidate
   blob identity.
3. Execute S10-G0 through S10-G5 against that immutable candidate in order.
4. At G5 verify equivalent detached environments, identical commands, complete node
   sets, non-empty signature equality, valid execution, and test summary/count.
5. Only then generate G6 Evidence, repeat G7 from the same SHA, and perform an
   independent G8 rereview.

## Assumptions Forbidden

- Q01 validity implies every historical validation failure is satisfied.
- support authority may provide run-local identity, timing, outcome, or missing hash.
- equal values may be coalesced into synthetic historical truth.
- raw equal failure counts prove `PROVEN_PREEXISTING`.
- mutable worktree content equals HEAD or may be labeled with HEAD.
- focused tests on an uncommitted worktree validate a detached stale candidate.
- Evidence generation may precede committing/freezing the exact implementation.

## Next Action

IMPLEMENT_RESOLVED_FIX

Final diagnosis status: RESOLVED
