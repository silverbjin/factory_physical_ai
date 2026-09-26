# TASK-SIM-Q01-MIN — Minimal Simulation Provenance Qualification

> Lane: Simulation
> Type: Additive architecture scope / qualification contract
> Status: `MIN_Q01_CONTRACT_FROZEN`
> Predecessor design: `TASK-SIM-Q01`
> Downstream consumer: `TASK-SIM-010`
> Architectural decision: `Q01_MINIMAL_REQUIRED`
> Runtime qualification executed: NO
> Independent acceptance: NO

## 1. Purpose and supersession boundary

This contract freezes the minimum additive provenance required to unblock the
frozen `TASK-SIM-010` observability/regression workflow. It supersedes the
Full-Q01 readiness scope only for the `TASK-SIM-010` dependency gate.

`TASK-SIM-Q01.md`, its implementation, and its history remain intact. This
contract does not claim that the Full-Q01 design never existed, does not
delete its implementation, and does not alter accepted predecessor state.

MIN-Q01 is not a semantic requalification of every internal predecessor
scenario. It qualifies only run-local claims that `TASK-SIM-010` cannot obtain
truthfully from immutable accepted Evidence, and it resolves supporting
version/source authority directly from immutable Git state where no new run
is required.

## 2. Compatibility identity and task result

MIN-Q01 retains the existing canonical Q01 machine contract so current tooling
and the future SIM-010 consumer do not require a token or artifact migration:

```text
Evidence task_id: TASK-SIM-Q01
Evidence path: results/simulation/SIM-Q01_provenance_qualification.json
Acceptance path: results/reviews/SIM-Q01_acceptance.json
READY: SIM_PROVENANCE_QUALIFICATION_READY
BLOCKED: SIM_PROVENANCE_QUALIFICATION_BLOCKED
```

`TASK-SIM-Q01-MIN` is the architecture/scope contract governing which
subjects participate in that decision. It does not introduce
`SIM_MIN_PROVENANCE_QUALIFICATION_*` tokens because doing so would require a
breaking SIM-010 consumer change before qualification.

The Full-Q01 Markdown report is not a prerequisite for SIM-010 consumption.
It may remain as a useful explanatory artifact, but its absence cannot make
MIN-Q01 BLOCKED.

## 3. Immutable authority and Contract B

All predecessor resolution follows Contract B:

```text
Acceptance
  -> accepted_commit
  -> exact task-declared Evidence blob at accepted_commit
  -> recomputed SHA256
  -> task-specific result
```

`accepted_commit` is authoritative. A current-worktree Evidence copy is never
predecessor authority.

The frozen predecessor bindings are unchanged from `TASK-SIM-Q01`:

| Task | Accepted commit | Evidence path | Evidence SHA256 |
|---|---|---|---|
| TASK-SIM-004 | `b7e8266abd17f48c18cca94d9433db50fd55464d` | `results/simulation/SIM-004_navigation_backend.json` | `b4c0ce91dde6c2f92c57ea6a227149362279993dee0dec4fd1ab12877e73f1d9` |
| TASK-SIM-005 | `542514a4d10bc03087834e8a5f672d53afe6aa21` | `results/simulation/SIM-005_mujoco_vla_backend.json` | `f4d41fdb1f13978e1b1e5c91b95e31b38a69825a0d432a8284ff7731a3beb84f` |
| TASK-SIM-007 | `228eb7745aa05c230e1b272184601b5afd53853b` | `results/simulation/SIM-007_mission_integration.json` | `7247f8db76c874e533f615f1c8c3f32febb7a7e2377790ff05e3e93320531711` |
| TASK-SIM-008 | `ea91e0c16412e20c8cae66355a1a39129919dd42` | `results/simulation/SIM-008_normal_system_e2e.json` | `ebf0ef0a27114e3c04fa6bec05aa3eef792fdfc282d2be009640bac7ecc26290` |
| TASK-SIM-009 | `67bde0e1f29c3f974bf3f0b29dff3f3aaa38e5be` | `results/simulation/SIM-009_failure_recovery.json` | `91d10e5bb4fb7ca1b62c325885bec276c6ef6231c6baa0424f3213702be3216e` |

## 4. Frozen required operation manifest

MIN-Q01 requires exactly eleven new operation subjects.

### SIM-008 — one subject

| Subject ID | Accepted scenario |
|---|---|
| `q01-sim008-normal-system-authority` | `SIM_NORMAL_BRAKE_ECU_LINE_B` |

### SIM-009 — ten subjects

| Subject ID | Accepted scenario |
|---|---|
| `q01-sim009-SIM009-NAV-BLOCKED` | `SIM009-NAV-BLOCKED` |
| `q01-sim009-SIM009-NAV-ABORTED` | `SIM009-NAV-ABORTED` |
| `q01-sim009-SIM009-NAV-TIMEOUT-RETRY` | `SIM009-NAV-TIMEOUT-RETRY` |
| `q01-sim009-SIM009-NAV-TF-UNAVAILABLE` | `SIM009-NAV-TF-UNAVAILABLE` |
| `q01-sim009-SIM009-VLA-GRASP-MISS` | `SIM009-VLA-GRASP-MISS` |
| `q01-sim009-SIM009-VLA-CONTACT-LOSS` | `SIM009-VLA-CONTACT-LOSS` |
| `q01-sim009-SIM009-VLA-WORKSPACE-LIMIT` | `SIM009-VLA-WORKSPACE-LIMIT` |
| `q01-sim009-SIM009-VLA-TIMEOUT` | `SIM009-VLA-TIMEOUT` |
| `q01-sim009-SIM009-VLA-AMBIGUOUS` | `SIM009-VLA-AMBIGUOUS` |
| `q01-sim009-SIM009-VLA-UNKNOWN` | `SIM009-VLA-UNKNOWN` |

No other operation subject participates in MIN-Q01 readiness.

## 5. Non-execution authority

The following authority is resolved from immutable accepted Git objects and
does not require a new MIN-Q01 execution.

### SIM-004

- component/version and runtime identity;
- world authority;
- bridge and runner source authority.

No standalone SIM-004 Q01 operation is required.

### SIM-005

- MuJoCo version;
- model, scene, configuration, and source authority;
- version-wide seed/timestep and accepted initial-state authority.

No standalone SIM-005 Q01 operation is required. In particular,
`mujoco-invalid-observation` is not a MIN-Q01 subject, and defects exclusive
to that Full-Q01 standalone path cannot block MIN-Q01.

### SIM-007

- profile identity;
- profile/source/configuration authority resolved from the accepted Git tree;
- accepted aggregate outcome semantics.

No new SIM-007 runtime or profile-qualification session is required.

Version-wide authority cannot replace a run-local claim for a required
SIM-008 or SIM-009 subject.

## 6. Applicability model

Every run-local field is classified as exactly one of `REQUIRED`, `OPTIONAL`,
or `NOT_APPLICABLE` for the concrete subject and observed execution path.

- When simulator execution occurs, structured simulator timing is `REQUIRED`.
- When a scenario truthfully terminates before simulator physics starts,
  physics measurement and physics timing are `NOT_APPLICABLE`.
- `NOT_APPLICABLE` must be explicit and justified by structured execution
  state; absence alone cannot imply it.
- A missing `REQUIRED` field makes the subject and MIN-Q01 `BLOCKED`.
- Wall time, log timestamps, filesystem timestamps, expected values, and
  historical Evidence cannot substitute for structured simulator time.
- Expected values may validate actual observations but may not fabricate them.

This policy preserves valid early rejection, timeout, unavailable, ambiguous,
unknown, and accepted non-success outcomes without weakening provenance
integrity.

## 7. Required SIM-008 claims

`q01-sim008-normal-system-authority` must prove, from one new bounded run:

- exact immutable SIM-008 predecessor binding and scenario identity;
- same-run correlation identity;
- world and system authority bound to the execution;
- exact execution configuration;
- semantically distinct bridge and launch/run authorities;
- structured simulator timing;
- bounded execution/cleanup state;
- actual semantic outcome.

No historical run-local backfill is permitted.

## 8. Required SIM-009 claims

Each of the ten subjects must prove:

- exact immutable SIM-009 predecessor and scenario binding;
- the accepted outcome used only as a comparison oracle;
- actual new-run correlation identity;
- run-local configuration authority;
- Gazebo world authority or MuJoCo model/scene authority where applicable;
- structured simulator timing when simulator execution occurred;
- explicit `NOT_APPLICABLE` timing/measurement when structured execution
  state proves termination before simulator physics;
- applicable retry, recovery, reconciliation, and Verification semantics;
- execution/cleanup state and actual semantic outcome.

Association by backend name, array position, execution order, timestamp
proximity, or cross-scenario reuse is forbidden.

## 9. Explicit exclusions from the readiness gate

The following do not block MIN-Q01:

- standalone SIM-004 Q01 operations;
- standalone SIM-005 Q01 operations;
- standalone SIM-005 `mujoco-invalid-observation` qualification;
- new SIM-007 runtime/profile qualification sessions;
- Full-Q01 25-subject completeness;
- Full-Q01 Markdown report completion.

Existing implementation for these paths remains in the repository and its
history. Exclusion from MIN-Q01 makes no positive claim that those paths
passed.

## 10. Evidence and downstream consumption

Canonical machine Evidence remains
`results/simulation/SIM-Q01_provenance_qualification.json`. Only the eleven
operation subjects in Section 4 participate in its MIN-Q01 readiness
decision. Supporting SIM-004/SIM-005/SIM-007 authority must be represented as
immutable authority bindings, not additional required operation subjects.

After independent Acceptance, SIM-010 may consume a claim only through:

```text
Q01 Acceptance
  -> accepted_commit
  -> exact canonical Q01 Evidence blob
  -> recomputed Evidence SHA256
  -> matching frozen predecessor binding
  -> unique MIN-Q01 subject/scenario/run identity
  -> declared claim_scope and applicability
```

SIM-010 must not infer that Full-Q01, standalone SIM-004/SIM-005 operations,
or SIM-007 runtime qualification passed.

After MIN-Q01 Acceptance, SIM-010 resumes at its Q01-aware resolver and
Evidence-regeneration step using accepted MIN-Q01 Evidence together with the
immutable accepted predecessor Evidence. SIM-010 then reruns focused
validation, deterministic/applicable regression checks, Evidence generation,
and its review lifecycle.

## 11. Completion gate

MIN-Q01 is complete only when all conditions hold:

- [ ] Contract-B predecessor bindings are verified.
- [ ] The one required SIM-008 subject completed.
- [ ] The ten required SIM-009 subjects completed.
- [ ] Every operation subject uniquely binds its predecessor and scenario.
- [ ] SIM-008 distinct bridge and launch/run authority is proven.
- [ ] Applicable SIM-009 run-local config/world/model/scene authority is proven.
- [ ] Structured simulator timing is present where `REQUIRED`.
- [ ] Legitimate pre-physics fields are explicitly `NOT_APPLICABLE`.
- [ ] No historical run-local backfill occurred.
- [ ] No cross-task result reuse occurred.
- [ ] No cross-scenario result reuse occurred.
- [ ] Canonical machine Evidence was generated.
- [ ] Independent Review returned `ACCEPT`.
- [ ] Canonical Acceptance was recorded.

Only then may SIM-010 consume MIN-Q01.

## 12. Protected scope and validation

Implementation must not modify accepted SIM-004, SIM-005, SIM-007, SIM-008,
or SIM-009 Acceptance/Evidence, the frozen SIM-010 state, or historical
Full-Q01 records.

Validation must prove:

- the machine-readable scope contains exactly one SIM-008 and ten SIM-009
  operation subjects with no duplicates;
- every required subject has an explicit predecessor/scenario binding;
- excluded Full-Q01 subject classes do not enter the readiness set;
- `REQUIRED` and `NOT_APPLICABLE` are distinct and fail closed;
- missing required provenance, wrong binding, or ambiguous reuse blocks;
- canonical Evidence and Acceptance use the unchanged compatibility identity
  and decision tokens.

## 13. Scope reopening rule

This scope may expand only through a new explicit architecture decision. If
implementation discovers a requirement not represented here, it must report
`MIN_Q01_SCOPE_REOPEN_REQUIRED` with the new requirement, authoritative
SIM-010 dependency, reason this freeze missed it, and minimum contract change.
It must not silently add a subject or claim.
