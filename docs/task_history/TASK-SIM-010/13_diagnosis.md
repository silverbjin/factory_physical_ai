# Diagnosis — TASK-SIM-010

- Status: RESOLVED
- Trigger: accepted `TASK-SIM-Q01-MIN` authority now exists, but the frozen SIM-010 implementation predates Q01 consumption
- Triggering status: `SIM_OBSERVABILITY_REGRESSION_BLOCKED` / `NOT READY FOR INDEPENDENT RE-REVIEW`
- Fault domain: `SIM010_Q01_INTEGRATION_GAP`
- Architecture decision: `ADDITIVE_Q01_BINDING_REQUIRED`
- Source modification performed: NO

## 1. Frozen state and lifecycle

The SIM-010 resume worktree is clean on branch `task/sim-010-resume` at:

```text
ff48f751489800132099b7c3e8ac2ad7435c9b73
```

This is the frozen qualification handoff boundary. Its source implementation is
the implementation checkpoint at `3e528e218023df76ac86c1c82d8b4833e6f064fc`;
the later SIM-010 commits preserve history and frozen BLOCKED Evidence. The
Evidence at the handoff reports:

- `SIM_OBSERVABILITY_REGRESSION_BLOCKED`;
- deterministic replay `PASS`;
- normal/failure suite coverage `PASS`;
- physics semantic regression `BLOCKED` with no validated Gazebo or MuJoCo
  physics rows;
- focused validation `23 passed` when rerun in this diagnosis;
- a recorded full-suite result of four failures classified
  `PROVEN_PREEXISTING` against `6909c6cceb727598570f6e170ae8d1d293418c9a`.

The current lifecycle state is therefore post-Fix 12, before independent
re-review, with the historical resolver corrections complete and the
predecessor qualification dependency formerly unresolved. Q01 has since been
accepted, but no Q01-aware SIM-010 correction has been implemented.

Commit `327e90af22a6453bfc4141a6ebfa9de265bfa4b8` is a child of the resume base
that adds or changes only Q01 planning, proposal, and task documents. It has no
SIM-010 source, runner, test, or Evidence delta and is not the SIM-010
implementation base.

The full-repository regression baseline remains:

```text
6909c6cceb727598570f6e170ae8d1d293418c9a
```

It is an ancestor of the resume base, but it is not the resume base.

## 2. Accepted Q01 authority verification

The canonical Q01 acceptance chain was verified without changing or
regenerating any Q01 artifact:

```text
acceptance recording commit:
  a1f1539c27f61fb2ce52aed33ceaf1bfe343912c
acceptance path:
  results/reviews/SIM-Q01-MIN_acceptance.json
acceptance SHA256:
  719e20397526bb416eb71235a80fdf93b1fecfb04131319b8114c32023476c73
acceptance task/status/workflow:
  TASK-SIM-Q01-MIN / ACCEPT / true
accepted commit:
  b55bc4fc2435e83c3761457b92d9e14892e39435
evidence path:
  results/simulation/SIM-Q01_provenance_qualification.json
evidence SHA256:
  dbd2fc20f6072f8889466fff29b80ec874d105b37c5633e909c633facdb2eb6a
evidence task/result:
  TASK-SIM-Q01 / SIM_PROVENANCE_QUALIFICATION_READY
```

The Q01 Evidence blob at the accepted commit contains exactly eleven unique
subjects, reports `subject_count = 11`, and has no missing, extra, or
binding-error subject IDs. Its SIM-004, SIM-005, SIM-007, SIM-008, and SIM-009
predecessor bindings exactly match the corresponding frozen accepted commit,
Evidence path, and recomputed Evidence SHA256.

The split between acceptance task ID `TASK-SIM-Q01-MIN` and compatibility
Evidence task ID `TASK-SIM-Q01` is intentional and must be validated
explicitly. A generic task-ID equality rule would incorrectly reject the
accepted contract.

## 3. Current resolver behavior

The frozen resolver in
`src/simulation_runtime/observability_regression.py` currently:

1. defines source tasks only as `SIM-003` through `SIM-009`;
2. reads each predecessor Acceptance from the current checkout;
3. resolves the declared Evidence from the Acceptance's immutable accepted
   commit and recomputes its SHA256;
4. validates task-specific result tokens and rich/minimal Acceptance shapes;
5. separates accepted-source rows from explicit task-specific run extraction;
6. binds SIM-009 version-wide Gazebo or MuJoCo authority through exact
   SIM-004/SIM-005 accepted bindings;
7. fails incomplete correlation, source hashes, provenance, scenario outcome,
   replay, or physics checks closed; and
8. compares current and baseline pytest node IDs plus non-empty normalized
   failure signatures.

The resolver has no Q01 Acceptance locator, Q01 expected result, Q01 Evidence
path, Q01 subject extractor, `claim_scope` validation, applicability model, or
historical-versus-qualification authority namespace. The runner also executes
the current mutable checkout while only the baseline is detached. Therefore
accepted Q01 consumption is not supported now.

The frozen output's remaining run-validation failures are:

| Historical source | Existing role | Frozen validation gap |
|---|---|---|
| SIM-004 | accepted Gazebo component authority and historical runs | structured simulation time absent for three historical runs |
| SIM-005 | accepted MuJoCo component authority and historical runs | trace ID absent for seven historical runs |
| SIM-007 | accepted profile/aggregate authority | source/config hashes absent on four normalized aggregates |
| SIM-008 | accepted normal oracle | distinct bridge and launch authority absent |
| SIM-009 | accepted failure oracle and deterministic scenarios | run-local config, world/model, and timing absent on ten physics scenarios |

Q01 does not repair the first three historical artifacts or mutate the last
two. It adds new, independently accepted observations for the authorized
SIM-008/SIM-009 subjects and immutable supporting authority for
SIM-004/SIM-005/SIM-007.

## 4. Requirement authority split

The normalized model must keep historical truth and Q01 qualification as two
linked but non-interchangeable observations.

| Requirement | Historical accepted authority | Accepted Q01 authority | Decision |
|---|---|---|---|
| R1 accepted-source index | Exact SIM-003 through SIM-009 Acceptance, accepted commit, Evidence path, and hash | Q01 is an additional qualification-source binding, not a replacement predecessor | Historical authority remains sufficient for the required predecessor index; add a separate Q01 binding record |
| R2 common correlation | Historical accepted scenario/oracle traces, deterministic contract rows, and Verification rows | Same-run correlation for the one SIM-008 and ten SIM-009 qualification subjects | Combined; Q01 fills only its own new-run correlation and must not backfill historical rows |
| R3 backend provenance | Component/version and accepted source authority, including SIM-004/SIM-005/SIM-007 support | Run-local config and world/model authority for the eleven subjects | Combined, with field-level claim scope |
| R4 Gazebo provenance | ROS 2/Gazebo/component and historical source authority | Distinct SIM-008 bridge/run configuration, run-local Gazebo config/world, structured time, and bounded cleanup | Q01 is required for the authorized Gazebo run-local observations |
| R5 MuJoCo provenance | MuJoCo version, model/scene/config, seed/timestep, and accepted initial-state authority | SIM-009 VLA run-local config/model plus required or explicitly not-applicable timing | Q01 is required for the authorized MuJoCo run-local observations |
| R6 deterministic replay | Accepted SIM-009 deterministic contract scenarios and lifecycle/decision oracles | No Q01 subject is an L0 deterministic replay subject | Historical authority only; Q01 rows must not manufacture replay PASS |
| R7 physics semantic regression | Accepted scenario IDs, expected decisions/outcomes, lifecycle semantics, invariants, and tolerances | Actual qualified Gazebo/MuJoCo observations and applicability | Combined; compare historical oracle to Q01 observation |
| R8 normal/failure coverage | SIM-008 normal scenario plus all sixteen accepted SIM-009 mandatory scenario IDs | Qualification completeness for the one normal and ten physics-failure subjects only | Historical authority defines coverage; Q01 qualifies exactly the frozen subset without expanding it |
| R9 Simulation-only labeling | Historical accepted artifacts and SIM-010 output label | Q01 Evidence has `simulation_only = true` | Both inputs and output must pass the label gate |
| R10 Evidence integrity | Immutable predecessor Acceptance/Evidence chain | Immutable Q01 Acceptance/Evidence chain, exact predecessor bindings, scope, uniqueness, and applicability | Combined fail-closed gate |
| R11 full regression | Not a predecessor claim | Not a Q01 claim | Must be produced by SIM-010 from an immutable candidate commit versus baseline `6909c6c...` |
| R12 task result | Supplies historical inputs | Supplies additive qualification inputs | Derived only after all SIM-010 gates pass |

Historical SIM-004/SIM-005/SIM-007 rows remain truthful accepted source
authority. Their missing historical run-local fields must not be declared
complete and must not be filled from Q01. Under the MIN-Q01 contract they are
supporting authority records, not required new operation subjects. SIM-010's
regression-subject set must therefore be distinct from its accepted-source
index.

## 5. Exact eleven-subject mapping

Each normalized Q01 record must retain these common fields:

```text
authority_kind = qualification_observation
qualification_task_id = TASK-SIM-Q01-MIN
qualification_evidence_task_id = TASK-SIM-Q01
qualification_accepted_commit = b55bc4fc2435e83c3761457b92d9e14892e39435
qualification_evidence_sha256 = dbd2fc20f6072f8889466fff29b80ec874d105b37c5633e909c633facdb2eb6a
claim_scope = run_local
simulation_only = true
subject_id = exact Q01 subject ID
qualification_run_id = exact Q01 value
predecessor_binding = exact frozen predecessor tuple
```

Identity is copied byte-for-byte from each subject's
`correlation_identity`. The SIM-008 subject is mission-scoped and requires
`mission_id`, `request_id`, and `trace_id`; no action ID may be invented.
Every SIM-009 subject is action-bound and requires all four identity fields.

| Subject / Q01 JSON pointer | Historical oracle | Normalized profile and component | Run-local provenance and applicability | Actual semantic observation |
|---|---|---|---|---|
| `q01-sim008-normal-system-authority` `/qualification_subjects/0` | SIM-008 `/scenario` + `/execution`, `SIM_NORMAL_BRAKE_ECU_LINE_B` | `gazebo`, `sim008-normal-system-e2e-v1` | bridge `b00fdf7c...`, launch/run `1da47e9d...`, system `f7716c41...`, world `fff98b8a...`; time/physics REQUIRED = `37.704` s | `success`, `completed` |
| `q01-sim009-SIM009-NAV-BLOCKED` `/qualification_subjects/2` | SIM-009 `/scenarios/3` | `gazebo`, `sim004-navigation-backend-v2` | run config `4df8805c...`, world `c26bf727...`; REQUIRED = `38.808` s | `FAIL_CLOSED`, `failure`, `failed` |
| `q01-sim009-SIM009-NAV-ABORTED` `/qualification_subjects/1` | SIM-009 `/scenarios/4` | `gazebo`, `sim004-navigation-backend-v2` | run config `4df8805c...`, world `c26bf727...`; REQUIRED = `39.003` s | `FAIL_CLOSED`, `failure`, `failed` |
| `q01-sim009-SIM009-NAV-TIMEOUT-RETRY` `/qualification_subjects/4` | SIM-009 `/scenarios/5` | `gazebo`, `sim004-navigation-backend-v2` | run config `4df8805c...`, world `c26bf727...`; REQUIRED = `40.488` s | `RETRY`, `pending`, `unknown`; preserve nested reconciliation/retry identity and single-side-effect proof |
| `q01-sim009-SIM009-NAV-TF-UNAVAILABLE` `/qualification_subjects/3` | SIM-009 `/scenarios/6` | `gazebo`, `sim004-navigation-backend-v2` | run config `4df8805c...`, world `c26bf727...`; REQUIRED = `48.804` s | `FAIL_CLOSED`, `failure`, `failed` |
| `q01-sim009-SIM009-VLA-GRASP-MISS` `/qualification_subjects/7` | SIM-009 `/scenarios/7` | `mujoco`, `sim005-mujoco-vla-backend-v1` | run config `34c09006...`, model `21fcb775...`; REQUIRED = `0.8` s | `FAIL_CLOSED`, `failure`, `failed` |
| `q01-sim009-SIM009-VLA-CONTACT-LOSS` `/qualification_subjects/6` | SIM-009 `/scenarios/8` | `mujoco`, `sim005-mujoco-vla-backend-v1` | run config `34c09006...`, model `21fcb775...`; REQUIRED = `0.8` s | `FAIL_CLOSED`, `failure`, `failed` |
| `q01-sim009-SIM009-VLA-WORKSPACE-LIMIT` `/qualification_subjects/10` | SIM-009 `/scenarios/9` | `mujoco`, `sim005-mujoco-vla-backend-v1` | run config `34c09006...`, model `21fcb775...`; time/physics NOT_APPLICABLE only because structured state says simulator and physics did not start | `FAIL_CLOSED`, `failure`, `failed` |
| `q01-sim009-SIM009-VLA-TIMEOUT` `/qualification_subjects/8` | SIM-009 `/scenarios/10` | `mujoco`, `sim005-mujoco-vla-backend-v1` | run config `34c09006...`, model `21fcb775...`; time/physics NOT_APPLICABLE only because structured state says simulator and physics did not start | `RECONCILE`, `pending`, `unknown`; preserve reconciliation |
| `q01-sim009-SIM009-VLA-AMBIGUOUS` `/qualification_subjects/5` | SIM-009 `/scenarios/11` | `mujoco`, `sim005-mujoco-vla-backend-v1` | run config `34c09006...`, model `21fcb775...`; time/physics NOT_APPLICABLE only because structured state says simulator and physics did not start | `FAIL_CLOSED`, `failure`, `failed`, uncertain outcome kind |
| `q01-sim009-SIM009-VLA-UNKNOWN` `/qualification_subjects/9` | SIM-009 `/scenarios/12` | `mujoco`, `sim005-mujoco-vla-backend-v1` | run config `34c09006...`, model `21fcb775...`; REQUIRED = `0.8` s | `RECONCILE`, `pending`, `unknown`; preserve reconciliation |

The ellipsized hashes above are display abbreviations only. The implementation
must compare and record the complete 64-character values from the accepted
Q01 blob.

No subject outside this table is authorized. In particular, SIM-004,
SIM-005, and SIM-007 Q01 data may appear only as supporting immutable authority
bindings; it may not become an additional operation subject.

## 6. Claim-scope and predecessor-binding enforcement

### `claim_scope`

- Every qualification subject must declare exactly `run_local`.
- A run-local claim applies only to that subject's new qualification run,
  scenario, identity, configuration, timing/applicability, and observed
  outcome. It cannot fill a field in the historical accepted run.
- Every entry in `immutable_authority_bindings` must declare exactly
  `immutable_accepted_authority` and may provide only its declared claim
  allowlist. It cannot provide run-local identity, timing, or outcome.
- `REQUIRED` timing/physics fields must contain an actual structured
  observation. `NOT_APPLICABLE` must contain the accepted justification and
  structured `simulator_started = false` and `physics_started = false` state.
  Absence, wall time, an expected value, or historical data cannot substitute.
- Unknown scope, extra subject, undeclared claim, missing required value, or
  contradictory applicability blocks the subject and final result.

### `predecessor_binding`

Validation must resolve, independently and in order:

```text
frozen predecessor Acceptance
  -> accepted_commit
  -> task-declared Evidence blob at that commit
  -> recomputed Evidence SHA256
  -> expected predecessor result
```

Each Q01 `predecessor_binding` must then equal that four-field tuple exactly.
The bound scenario must exist exactly once in the accepted predecessor blob,
and its component version/backend must agree with the Q01 subject. Association
by array position alone, backend name alone, execution order, timestamp
proximity, or a mutable worktree file is forbidden.

The Q01 Acceptance itself must be loaded from its pinned acceptance-recording
commit and path, not from an assumed merge or the Q01 worktree. Then its
accepted commit, exact Evidence path, recomputed Evidence hash, compatibility
task ID, result token, validation status, and exact subject set are checked.
Missing Git objects fail closed; Q01 history must not be merged merely to make
the Evidence visible.

## 7. Duplicate-authority prevention

Historical and qualification observations must remain separately namespaced:

```text
historical_oracle:
  predecessor task + accepted commit + evidence path + scenario/source path

qualification_observation:
  Q01 accepted commit + Q01 evidence hash + subject_id + qualification_run_id
```

For an authorized scenario, the normalized regression row is a link containing
one historical oracle reference and one Q01 observation reference. It is not a
flattened replacement run. Historical data supplies expected semantics; Q01
supplies the actual qualified observation. Equal fields are compared, not
silently coalesced. A disagreement blocks the row.

Uniqueness must be enforced for subject ID, qualification run/scenario
identity, and the fixed subject-to-predecessor-scenario mapping. A second Q01
subject for the same authorized mapping, a historical row relabeled as Q01, or
a Q01 row relabeled as the historical run is ambiguous duplicate authority and
must fail closed.

## 8. Replay, physics, and full regression consumption

### Deterministic replay

R6 continues to consume only validated historical L0 deterministic rows and
their accepted decision/lifecycle oracles. All eleven Q01 rows are
`replay_applicable = false`. The nested retry/reconciliation proof in
`NAV-TIMEOUT-RETRY` is checked for semantic traceability but cannot itself
create a deterministic replay PASS. Replay must still fail closed if no valid
historical deterministic row exists or if a rerun disagrees on decision or
lifecycle.

### Physics semantic regression

R7 consumes the Q01 observation side of the linked rows and the historical
accepted scenario side as the oracle. It must compare scenario/component
identity, outcome/status/decision, required lifecycle/retry/reconciliation
semantics, declared invariants/tolerances, provenance hashes, and
applicability. Gazebo and MuJoCo must both have at least one validated
applicable physics observation. Explicit pre-physics `NOT_APPLICABLE` subjects
remain traceable but are not counted as physics measurements. No bitwise
physics trace identity or physical/production performance claim is permitted.

### Full repository regression

The final full regression must run the identical declared command in two clean,
detached worktrees under the same interpreter/environment:

```text
current immutable SIM-010 candidate commit
6909c6cceb727598570f6e170ae8d1d293418c9a
```

The current mutable checkout is not sufficient. A current PASS is `PASS`. A
current failure is `PROVEN_PREEXISTING` only when baseline execution succeeds
as an observation and the complete failed-node set and each non-empty stable
failure signature match exactly. Equal counts, similar names, or node IDs
without matching signatures are insufficient. Checkout, execution, parse, or
cleanup failure, an empty signature, an added/removed node, or a changed
signature yields `POSSIBLY_TASK_RELATED` and blocks SIM-010.

## 9. Minimum authorized correction boundary

A source change is required, but only in the downstream SIM-010 consumer:

- `tasks/TASK-SIM-010.md`: a narrow in-place Q01 integration addendum;
- `src/simulation_runtime/observability_regression.py`: pinned Q01 acceptance
  and Evidence resolution, exact subject mapping, scope/applicability and
  predecessor validation, separate authority namespaces, and linked
  replay/physics consumption;
- `scripts/run_simulation_observability_regression.py`: immutable candidate
  versus immutable baseline execution and fail-closed result capture;
- `tests/test_simulation_observability_regression.py`: exact positive mapping
  plus missing/wrong Q01 commit, path, hash, task/result, subject set,
  predecessor binding, scope, applicability, duplicate authority, cross-run
  reuse, replay exclusion, physics oracle mismatch, and baseline-signature
  negatives;
- only after all pre-evidence gates pass,
  `results/simulation/SIM-010_observability_regression.json` and
  `docs/simulation/simulation_observability_regression_v1.md` may be
  regenerated.

The correction must not modify any accepted Q01 or SIM-003 through SIM-009
artifact, Acceptance, Evidence, accepted commit, contract, historical task
record, orchestrator source, simulator behavior, or physics implementation.
It must not create a replacement SIM-010 task.

The canonical task currently names only SIM-008/SIM-009 dependencies and
SIM-003 through SIM-009 authority. A task-spec clarification is therefore
required before implementation. A narrow addendum to the existing
`TASK-SIM-010.md` is sufficient. It must pin the Q01 acceptance-recording
commit/path, accepted commit, Evidence path/hash/result, exact eleven-subject
set, authority split, claim-scope/applicability rules, duplicate prevention,
immutable-current regression rule, and correction boundary. No
`TASK-SIM-010-v2` is warranted.

## 10. Staged gates

The gates are strictly ordered; a failure prevents entry to the next gate.

| Gate | Required proof |
|---|---|
| S10-G0 `Q01_ACCEPTANCE_BINDING` | Resolve the pinned Q01 Acceptance recording object; verify `ACCEPT`, `workflow_complete`, accepted commit, exact Evidence blob/hash, compatibility task/result, validation PASS, and exact predecessor tuples. |
| S10-G1 `SUBJECT_MAPPING` | Prove set equality with the frozen eleven IDs, uniqueness, exact subject-to-task/scenario/component mapping, and absence of any additional operation subject. |
| S10-G2 `NORMAL_FAILURE_TRACEABILITY` | Build separate historical-oracle and Q01-observation references; enforce scope/applicability; compare the SIM-008 normal outcome and ten SIM-009 physical failure/recovery outcomes while retaining all sixteen historical failure scenarios in coverage. |
| S10-G3 `DETERMINISTIC_REPLAY` | Replay only valid historical deterministic inputs; compare decision and lifecycle; prove all Q01 rows are excluded from replay authority. |
| S10-G4 `PHYSICS_SEMANTIC_REGRESSION` | Compare Q01 actuals to historical oracles, validate both Gazebo and MuJoCo, enforce invariants/tolerances and explicit pre-physics N/A, and prohibit bitwise/physical claims. |
| S10-G5 `FULL_REGRESSION_CLASSIFICATION` | Run identical full pytest commands at the immutable candidate and `6909c6c...`; require PASS or exact node-plus-signature proof; otherwise block. |
| S10-G6 `CANONICAL_SIM010_EVIDENCE` | Render a canonical-ready candidate containing all bindings, hashes, mappings, gate results, immutable source commit, and truthful READY/BLOCKED decision. Do not publish READY unless G0-G5 pass. |
| S10-G7 `REPEATABILITY_AND_FINALIZATION` | Repeat from the same immutable candidate, prove normalized output and decisions repeat, validate schema/hash and `git diff --check`, then publish/freeze the canonical Evidence and companion report. |
| S10-G8 `INDEPENDENT_REVIEW` | Independently review scope, contract, tests, Evidence, immutable regression proof, and absence of predecessor/Q01 mutation; only ACCEPT permits acceptance recording. |

## 11. Resume safety

The orchestrator is not safe to resume now. The frozen task contract does not
authorize or define the accepted Q01 binding, and the current resolver cannot
consume it. Resuming before the narrow addendum and Q01-aware correction are
present would at best regenerate the known BLOCKED shape and at worst invite
an unbounded interpretation of Q01 authority. No orchestrator command,
`--force`, Evidence generation, or source correction was executed during this
diagnosis.

## Final Decisions

primary_decision: SIM010_Q01_ADDITIVE_BINDING_CORRECTION_REQUIRED
q01_acceptance_verified: YES
sim010_resume_base_verified: YES
regression_baseline_verified: YES
sim010_current_state: INCOMPLETE_POST_FIX12_Q01_AUTHORITY_AVAILABLE_NOT_CONSUMED
q01_consumption_supported_now: NO
code_change_required: YES
subject_mapping_complete: YES_DIAGNOSIS_ONLY
claim_scope_enforcement_defined: YES
duplicate_authority_prevention_defined: YES
architecture_change_required: YES_NARROW_ADDITIVE_AUTHORITY_LAYER
task_spec_change_required: YES_NARROW_ADDENDUM_ONLY
authorized_correction_boundary: TASK_SIM010_SPEC_ADDENDUM_PLUS_OBSERVABILITY_RESOLVER_RUNNER_TESTS_AND_POST_GATE_OWNED_EVIDENCE_ONLY
gate_sequence: S10-G0>S10-G1>S10-G2>S10-G3>S10-G4>S10-G5>S10-G6>S10-G7>S10-G8
orchestrator_resume_ready: NO
first_next_action: ADD_NARROW_Q01_INTEGRATION_ADDENDUM_TO_EXISTING_TASK_SIM_010
