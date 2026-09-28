# Autonomous Gate Resolution — TASK-SIM-Q01-MIN / GATE-6 CANONICAL_11_SUBJECT

## 1. Starting State

Durable reports 11 through 16 established the converged runtime architecture,
the four passing SIM-009 NAV semantics, same-run correlation, and the first
successful NAV run-local provenance boundary. Report 16 stopped GATE-6 at:

```text
q01-sim009-SIM009-VLA-UNKNOWN
ValueError: MISSING_RUN_LOCAL_PROVENANCE
```

The producer trace in that report proved that every NAV subject already had a
current-run structured observation. This autonomous session therefore began
at the next same-gate invariant and did not reopen GATE-4 or GATE-5.

## 2. Gate Contract

GATE-6 requires exactly these eleven current-run subjects:

1. `q01-sim008-normal-system-authority`
2. `q01-sim009-SIM009-NAV-BLOCKED`
3. `q01-sim009-SIM009-NAV-ABORTED`
4. `q01-sim009-SIM009-NAV-TIMEOUT-RETRY`
5. `q01-sim009-SIM009-NAV-TF-UNAVAILABLE`
6. `q01-sim009-SIM009-VLA-GRASP-MISS`
7. `q01-sim009-SIM009-VLA-CONTACT-LOSS`
8. `q01-sim009-SIM009-VLA-WORKSPACE-LIMIT`
9. `q01-sim009-SIM009-VLA-TIMEOUT`
10. `q01-sim009-SIM009-VLA-AMBIGUOUS`
11. `q01-sim009-SIM009-VLA-UNKNOWN`

One valid execution must report eleven subjects, no missing/extra/binding
errors, valid run-local provenance for every subject, validation `PASS`, and
`SIM_PROVENANCE_QUALIFICATION_READY`.

GATE-7 requires a second fresh complete canonical execution with the same
subject semantics, new execution/correlation identities, valid fresh
provenance, complete cleanup, and no stale runtime processes.

## 3. Regression-Protected Baseline

The following remained frozen:

- immutable navigation runtime context and per-run isolation;
- shared SIM-008/SIM-009 readiness and owned cleanup;
- explicit private ROS action worker/context/executor;
- pre-goal semantic provenance boundaries;
- TIMEOUT-RETRY real two-attempt lifecycle;
- all four NAV semantic validators and outcomes;
- same-run request/goal correlation;
- one SIM-008 supplier and one SIM-009 suite supplier per canonical attempt;
- immutable Git predecessor binding;
- accepted Acceptance/Evidence, task scope, and frozen SIM-010.

The established focused baseline was 115 passing tests before the new
MuJoCo producer regression was added.

## 4. Resolution Ledger

### Cycle 1

**First failing invariant**

```text
q01-sim009-SIM009-VLA-UNKNOWN
run_local_provenance = null
collector = MISSING_RUN_LOCAL_PROVENANCE
```

**Fault domain**

`SAME_GATE`: this is one of the ten required SIM-009 subjects and its producer
feeds the same GATE-6 collector contract.

**Producer → adapter → collector trace**

The real `_vla_scenario()` result contained:

```text
result.status: unknown
reconciliation.observed_status: succeeded
measurement:
  scenario: mujoco-unknown
  physics_started: true
  authoritative_outcome: succeeded
```

`_sim009_sidecar_observation()` requires either real `steps` and
`timestep_seconds`, or an explicit pre-physics false/false state. The record
claimed physics had started but contained neither structured time field, so
the observer correctly returned `None`. `run_sim009_qualification()` preserved
that null value and the canonical collector correctly rejected it.

The first divergence was in `MuJoCoVLABackend.execute()`: the
`mujoco-unknown` branch recorded authoritative success without invoking
`_step_physics()`. Working physics-backed MuJoCo scenarios invoke that method
and retain `steps=400` and `timestep_seconds=0.002`.

**Root cause**

```yaml
root_cause: SIM009_VLA_UNKNOWN_STRUCTURED_PHYSICS_MEASUREMENT_DEFECT
expected_behavior: real bounded physics execution followed by an externally unknown result and authoritative succeeded reconciliation
actual_behavior: static physics_started=true record without a real step/time measurement
first_divergence: MuJoCoVLABackend.execute mujoco-unknown branch
same_gate: YES
architecture_change_required: NO
contract_change_required: NO
```

Accepted SIM-009 authority requires the external result to remain pending and
unknown until `action_status.get`, which returns observed status `succeeded`.
The correction preserves those semantics.

**RED**

Added
`test_sim009_unknown_reconciliation_retains_real_mujoco_simulation_time`.
It executes the real MuJoCo backend through `_vla_scenario()`, then invokes the
real sidecar producer. Before correction:

```text
assert observation is not None
AssertionError: assert None is not None
```

**Correction**

`src/simulation_runtime/mujoco_vla_backend.py` now runs the existing bounded
400-step nominal physics profile for `mujoco-unknown`, records the actual
measurement under scenario `mujoco-unknown`, adds the authoritative succeeded
state, and still returns the accepted external `pending/unknown` result.

No final data, time, identity, or reconciliation result is synthesized by the
Q01 adapter. The source is the current MuJoCo execution.

**Focused verification**

```text
tests/test_simulation_mujoco_vla_backend.py
tests/test_simulation_navigation_backend.py
tests/test_simulation_normal_system_e2e.py
tests/test_simulation_failure_recovery.py
tests/test_simulation_provenance_qualification.py

124 passed in 5.09s
py_compile: PASS
git diff --check: PASS
```

**Gate result after fix**

```text
GATE-6: PASS
new first failing invariant: NONE
```

Only one correction cycle was required.

## 5. Full Subject Sweep

The canonical artifact contains exactly eleven distinct required subjects.

| Subject | Source | Semantic decision/result | Cleanup |
| --- | --- | --- | --- |
| SIM-008 normal system | `gazebo_authoritative_observation` | success/completed | true |
| NAV-BLOCKED | `gz_stats` | FAIL_CLOSED/failure | true |
| NAV-ABORTED | `gz_stats` | FAIL_CLOSED/failure | true |
| NAV-TIMEOUT-RETRY | `gz_stats` | RETRY/pending | true |
| NAV-TF-UNAVAILABLE | `gz_stats` | FAIL_CLOSED/failure | true |
| VLA-GRASP-MISS | `mujoco_steps_times_timestep` | FAIL_CLOSED/failure | true |
| VLA-CONTACT-LOSS | `mujoco_steps_times_timestep` | FAIL_CLOSED/failure | true |
| VLA-WORKSPACE-LIMIT | `mujoco_no_physics_start` | FAIL_CLOSED/failure | true |
| VLA-TIMEOUT | `mujoco_no_physics_start` | RECONCILE/pending | true |
| VLA-AMBIGUOUS | `mujoco_no_physics_start` | FAIL_CLOSED/failure | true |
| VLA-UNKNOWN | `mujoco_steps_times_timestep` | RECONCILE/pending | true |

VLA-UNKNOWN now carries `400 * 0.002 = 0.8` seconds from its real current-run
MuJoCo execution.

## 6. Final Gate Verification

### GATE-6

Command:

```bash
PYTHONDONTWRITEBYTECODE=1 \
/home/jinho/projects/factory_physical_ai/.venv-sim/bin/python3 \
scripts/run_simulation_provenance_qualification.py \
  --output /tmp/SIM-Q01-MIN_preflight.json \
  --report /tmp/SIM-Q01-MIN_preflight.md
```

Actual result:

```json
{
  "task_specific_result": "SIM_PROVENANCE_QUALIFICATION_READY",
  "validation": {
    "binding_error_subject_ids": [],
    "extra_subject_ids": [],
    "missing_subject_ids": [],
    "status": "PASS",
    "subject_count": 11
  }
}
```

First artifact SHA-256:
`64f467e5996fc77378d3278a284be8994e184847df87adbf7de3fd923389be77`.

### GATE-7

A second complete fresh run wrote
`/tmp/SIM-Q01-MIN_repeatability.json` and `.md` and produced the same PASS
shape with eleven subjects and no validation errors.

```text
first SIM-009 qualification run:
  q01-sim009-e4f9ae27-a8de-405a-9109-f8ebccfa5a87
second SIM-009 qualification run:
  q01-sim009-24cea879-9cea-4569-b32c-0c8c72836699
second artifact SHA-256:
  aae239c9a48bcecf2aba0e94fe7b307ebe79e67fdc33f68335b68fa702c9b689
```

Comparison proved:

- identical exact eleven-subject sets;
- one distinct SIM-009 qualification run per execution;
- ten unique scenario execution IDs per SIM-009 run and no cross-run reuse;
- no correlation identity reused between runs;
- equivalent scenario/backend/applicability/provenance-source/semantic
  outcomes;
- all cleanup flags true;
- no surviving owned ROS, Gazebo, or private action-worker process.

```text
GATE-6 CANONICAL_11_SUBJECT: PASS
GATE-7 REPEATABILITY: PASS
```

## 7. Regression Verification

The gate-relevant focused suite is green at `124 passed`.

A supplementary whole-repository run produced:

```text
424 passed, 15 failed
```

The failures are outside this gate-resolution correction:

- one orchestrator model-policy fixture missing the now-required schema;
- three simulation-lane-gate expectations evaluated against the accumulated
  dirty task worktree;
- eleven verification-backend cases intentionally fail closed because the
  protected dirty SIM-004 worktree artifact does not match its accepted hash.

These failures neither occur in the gate-relevant baseline nor invalidate the
two successful canonical executions. They were not modified or repaired under
this task's protected-scope rules.

## 8. Protected Scope Verification

- `tasks/TASK-SIM-Q01-MIN.md` was not modified.
- Accepted predecessor Acceptance and Evidence were not modified in this
  autonomous session.
- Frozen SIM-010 was not modified.
- Protected dirty `results/simulation/SIM-004_navigation_backend.json` was
  preserved and was not reset, cleaned, restored, staged, or committed.
- No validator, semantic decision, budget, subject set, or applicability rule
  was weakened.
- No observation, structured time, identity, request, goal, or Evidence was
  fabricated.
- No orchestrator/resume command was run.
- No unrelated process was killed.

## 9. Final State

```text
resolution_cycles: 1
GATE-4: PASS (regression protected)
GATE-5: PASS (regression protected)
GATE-6: PASS
GATE-7: PASS
architecture_changed: NO
contract_changed: NO
ORCHESTRATOR_RESUME_READY: YES
```

## 10. Next Gate / Remaining Blocker

The authorized sequence ended at GATE-7. No gate invariant remains and no
additional gate was invented. The orchestrator was not resumed by this
session.

```text
remaining_blocker: NONE
```
