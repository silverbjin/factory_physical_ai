# TASK-SIM-Q01-MIN Run-Local Provenance Final Qualification

## 1. Trigger

The prior canonical preflight stopped while collecting
`q01-sim009-SIM009-NAV-BLOCKED` with:

```text
ValueError: MISSING_RUN_LOCAL_PROVENANCE
```

GATE-4 and GATE-5 were treated as regression-protected. This cycle changed
only the Gazebo structured-statistics acquisition boundary used by SIM-009
run-local provenance and its focused tests.

## 2. Run-local provenance contract

Repository authority defines one valid SIM-009 `run_local_provenance` value as:

```text
simulation_time:
  source: gz_stats | mujoco_steps_times_timestep | mujoco_no_physics_start
  seconds: numeric                         # required except pre-physics N/A
  execution_state:                         # required for pre-physics N/A
    simulator_started: false
    physics_started: false
configuration_sha256: 64-character SHA-256
world_model_sha256: 64-character SHA-256
source_paths:
  configuration: non-empty repository path
  world_model: non-empty repository path
```

The runtime sources are:

- Gazebo NAV: `/world/sim004_navigation_proxy_world/stats` in the active
  runtime's immutable `GZ_PARTITION`, plus hashes of the SIM-009 manifest and
  navigation world.
- MuJoCo VLA: the current row's `steps * timestep_seconds`, or the explicit
  structured pre-physics state, plus current configuration/model hashes.

Measurement occurs after the scenario operation has produced its row and
before that row is appended to the suite. The Gazebo runtime is suite-local,
but the observation is scenario-local: every applicable row receives its own
measurement. A suite-level value is not copied between scenarios.

`qualification_run_id` and `scenario_execution_id` are allocated before
startup in `run_failure_suite()`, attached as `qualification_attempt`, and
copied by `run_sim009_qualification()` into the record's
`execution_identity`. The provenance dictionary is bound by residing on that
same row; the collector verifies the execution identity and run identity
before constructing the subject.

All ten required SIM-009 subjects require a non-empty run-local value. The
only legitimate N/A shape is an operation proven to terminate before physics,
represented by `mujoco_no_physics_start` and the exact false/false execution
state. Historical values, accepted Evidence, suite-wide copying, cross-run
reuse, and cross-scenario reuse are forbidden.

The working SIM-008 path similarly obtains structured simulator time from its
current authoritative world observation and binds current world/system/bridge
and launch hashes; it does not use accepted Evidence as run-local data.

## 3. Producer to adapter to collector trace

A fresh controlled NAV-BLOCKED trace used the real shared SIM-009 runtime:

```text
qualification_run_id:
  q01-sim009-ac98e0a2-e53f-4de5-9546-7e3a11ae976c
scenario_execution_id:
  476670d9-1653-462a-b2f3-4456918e291e
runtime isolation:
  ROS_DOMAIN_ID=166
  GZ_PARTITION=sim004-b8883f9d9f83
Gazebo stats:
  simTime.sec=34
  simTime.nsec=974000000
row qualification_observation:
  source=gz_stats
  seconds=34.974
adapter run_local_provenance:
  source=gz_stats
  seconds=34.974
cleanup_complete: true
```

Boundary results:

| Boundary | Input key | Output key | Result |
| --- | --- | --- | --- |
| Gazebo transport | world stats topic | structured JSON | current partition value |
| scenario observer | `simTime` | `qualification_observation` | preserved |
| suite row | `qualification_observation` | same | preserved |
| Q01 adapter | row observation | `run_local_provenance` | preserved without rename loss |
| canonical collector | record provenance | subject timing/assets | accepted when non-empty |

Thus a successful measurement was not dropped by the adapter or collector.
The first defective boundary was producer acquisition: the prior producer made
one discovery-sensitive five-second CLI subscription and converted any
transient acquisition failure directly to an absent observation.

## 4. Root cause

```yaml
root_cause: SIM009_STRUCTURED_STATS_SIDECAR_LIFECYCLE_DEFECT
first_failing_invariant: q01-sim009-SIM009-NAV-BLOCKED requires non-empty current-run structured provenance
producer_has_measurement: conditional before fix; a transient first subscription was discarded
adapter_receives_measurement: YES when the producer returns it
collector_receives_measurement: YES when the adapter receives it
same_run_binding_present: YES
architecture_change_required: NO
```

The producer's fail-closed behavior was correct, but its single short
subscription made a transient transport-discovery miss final. Neither the
record adapter nor the canonical collector dropped a valid value.

## 5. RED reproduction

Added
`test_sim009_sidecar_retries_transient_stats_discovery_for_same_scenario`.
It uses the real sidecar producer contract and the same runtime object: the
first Gazebo stats acquisition raises the production timeout error and the
second returns structured `simTime`. Before correction the observer called the
source once, returned `None`, and the test failed with:

```text
assert len(observations) == 2
AssertionError: assert 1 == 2
```

The existing persistent-timeout test remains and proves that unavailable
structured provenance is not fabricated.

## 6. Bounded correction

`scripts/q01_execution_adapters.py` now:

- permits at most two stats acquisitions for one Gazebo scenario;
- uses the exact same runtime object, world topic, and immutable transport
  partition for both acquisitions;
- gives each subscription one bounded 15-second transport-discovery window;
- returns only a newly parsed current-run `simTime` value;
- still returns `None` after persistent failure.

No value is shared across scenarios or runs. No accepted or historical
Evidence is read. Collector validation and applicability rules are unchanged.

## 7. Focused tests

```text
PYTHONDONTWRITEBYTECODE=1 \
/home/jinho/projects/factory_physical_ai/.venv-sim/bin/python3 \
  -m pytest -q -p no:cacheprovider \
  tests/test_simulation_navigation_backend.py \
  tests/test_simulation_normal_system_e2e.py \
  tests/test_simulation_failure_recovery.py \
  tests/test_simulation_provenance_qualification.py

115 passed in 3.43s
```

The previous baseline was 114 tests. `py_compile` passed for the touched
production and test modules, and `git diff --check` passed.

## 8. Live SIM-009 producer/adapter validation

One post-correction shared live suite passed:

```text
qualification_run_id:
  q01-sim009-87df7d5e-f0c5-4a7f-aa39-3b24b60360eb
suite result: SIM_FAILURE_SUITE_READY
suite cleanup: true
distinct NAV scenario_execution_ids: 4

SIM009-NAV-BLOCKED
  semantic/correlation/provenance/cleanup: PASS
  gz_stats seconds: 33.795
SIM009-NAV-ABORTED
  semantic/correlation/provenance/cleanup: PASS
  gz_stats seconds: 34.005
SIM009-NAV-TIMEOUT-RETRY
  semantic/correlation/provenance/cleanup: PASS
  gz_stats seconds: 35.403
SIM009-NAV-TF-UNAVAILABLE
  semantic/correlation/provenance/cleanup: PASS
  gz_stats seconds: 42.141
```

This preserves GATE-4 and GATE-5.

## 9. GATE-6 canonical result

The exact preflight command was run. Two uninstrumented attempts reached the
collector but its combined guard did not identify which mapped input was
missing. A final diagnostic run instrumented the producer boundary without
changing execution semantics.

That run proved all four NAV rows carried current-run structured provenance:

```text
qualification_run_id:
  q01-sim009-7f1d5d14-f11d-48e6-888e-9917e251b651
NAV-BLOCKED:        gz_stats 33.210
NAV-ABORTED:        gz_stats 33.405
NAV-TIMEOUT-RETRY:  gz_stats 34.905
NAV-TF-UNAVAILABLE: gz_stats 42.963
```

The canonical run then exposed a new independent fault domain:

```text
SIM009-VLA-UNKNOWN
backend: mujoco
qualification_attempt: present
correlation source: present
qualification_observation: null
collector result: ValueError: MISSING_RUN_LOCAL_PROVENANCE
```

Per the task stop rule, no VLA repair was started. The aggregate was not
created, so `required_subjects`, `observed_subjects`, `missing`, `extra`, and
`binding_errors` were not emitted and neither requested `/tmp` artifact was
written.

```text
GATE-6 = BLOCKED
```

## 10. GATE-7 repeatability

Not run because GATE-6 did not pass.

```text
GATE-7 = BLOCKED_BY_GATE_6
```

## 11. Protected scope verification

- MIN-Q01 remains exactly one SIM-008 plus ten SIM-009 subjects.
- No task specification was modified in this cycle.
- No accepted predecessor Acceptance or Evidence was modified in this cycle.
- Frozen SIM-010 was not modified.
- The protected dirty SIM-004 result was not reset, restored, cleaned,
  rewritten, staged, or committed.
- No accepted semantic validator, decision, budget, or identity rule changed.
- No run-local provenance, request, attempt, or goal was fabricated.
- One SIM-009 suite remains the sole supplier per canonical attempt.
- No orchestrator or resume command was run.
- All completed live runs reported owned cleanup; no owned ROS, Gazebo, or
  action-worker process remained after verification.

## 12. Final readiness

```text
GATE-4 PASS
GATE-5 PASS
GATE-6 BLOCKED
GATE-7 BLOCKED_BY_GATE_6
ORCHESTRATOR_RESUME_READY = NO
```

The first remaining invariant is:

```text
q01-sim009-SIM009-VLA-UNKNOWN has no non-empty current-run structured
run_local_provenance; its MuJoCo sidecar observation is null.
```
