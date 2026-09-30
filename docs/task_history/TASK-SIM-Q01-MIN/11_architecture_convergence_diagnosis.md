# Architecture Convergence Diagnosis — TASK-SIM-Q01-MIN

## 1. Why This Diagnosis Was Triggered

MIN-Q01 has progressed through a serial chain of runtime and provenance
failures while its focused tests remained green:

1. SIM-008 lacked deterministic localization bootstrap.
2. SIM-008 left launch-owned descendants that contaminated later runs.
3. SIM-008 launch inherited an incomplete ROS environment.
4. SIM-009's accepted 33-second retry budget depended on a mutable SIM-008
   execution-window global.
5. SIM-009 maintained a second current-worktree accepted-Evidence consumer.
6. The canonical preflight now reaches SIM-009 but receives navigation rows
   with no mission/request/trace correlation because live navigation readiness
   fails before a request is created.

The current exception is:

```text
collect_qualification_subjects()
  -> collect_sim009_execution_result(...)
  -> ValueError: MISSING_RUN_LOCAL_CORRELATION
```

That exception was not modified in this diagnosis. It is a correct downstream
signal that a required operation result was not produced. The question here is
why the canonical path keeps exposing a new upstream condition only after the
previous one is repaired.

This diagnosis was read-only with respect to implementation and tests. The
only repository addition is this requested diagnosis report. The protected
dirty worktree, including `results/simulation/SIM-004_navigation_backend.json`,
was preserved.

## 2. Current Failure Sequence

The sequence is **BOTH** independent blocker unmasking and systemic
architectural fragmentation.

- Localization, launch environment, and immutable Git binding were real,
  individually valid defects. A fail-closed pipeline necessarily revealed
  some of them in dependency order.
- Their recurrence across adjacent call paths is not independent coincidence.
  Runtime configuration is partly process-global, session/bootstrap ownership
  is split between SIM-008 and SIM-009 wrappers, exceptions are collapsed at
  the SIM-009 boundary, and the canonical runner repeatedly invokes the same
  whole-suite supplier.
- The canonical preflight is consequently the first test that simultaneously
  exercises ROS environment materialization, process ownership, localization,
  private rclpy discovery, request identity, run-local provenance, collection,
  and aggregation.

The current failure is reached as follows:

```text
SIM-008 run
  -> GazeboSystemWorld mutates navigation timeout globals
  -> shared bounded runtime succeeds and cleans up
SIM-009 supplier
  -> creates GoalTrackedGazeboNav2Runtime
  -> start/bootstrap exception or false readiness is collapsed to live_ready=False
  -> NAV scenario returns before begin_scenario() and _action_request()
  -> raw result contains only result/error
  -> adapter correlation_identity is empty
  -> collector raises MISSING_RUN_LOCAL_CORRELATION
```

The validator must continue to reject this row. Adding identifiers after the
failure would invent a navigation request that never existed.

## 3. Actual Execution Graph

### 3.1 Canonical MIN-Q01 graph

```text
scripts.run_simulation_provenance_qualification.main
  -> resolve_predecessor_binding() for FROZEN tasks
  -> live_adapters()
  -> collect_qualification_subjects()
       -> required_subject_manifest()
       -> q01-sim008-normal-system-authority
            -> run_sim008_qualification()
            -> NormalSystemE2E(GazeboSystemWorld(...)).execute()
            -> collect_sim008_execution_result()
       -> each of ten q01-sim009-* subjects
            -> run_sim009_qualification()             [called again per subject]
            -> run_failure_suite()                    [runs all 16 scenarios]
            -> select requested scenario from mapping
            -> collect_sim009_execution_result()
  -> aggregate_qualification_evidence()
  -> write_qualification_artifacts()
```

A transient controlled invocation of the actual dispatcher measured:

```yaml
subjects: 11
sim008_supplier_calls: 1
sim009_supplier_calls: 10
```

Thus a successful canonical run would execute the complete 16-row SIM-009
suite ten times, then retain one different requested row from each suite. This
is not required by the frozen 11-subject contract and unnecessarily multiplies
runtime creation, rclpy initialization, process cleanup, and stale-state risk.

### 3.2 SIM-008 graph

```text
run_sim008_qualification()
  -> load_scenario()
  -> GazeboSystemWorld.__init__()
       -> mutate run_simulation_navigation timeout globals
       -> derive localization pose from SIM-008 scenario source region
       -> BoundedGazeboNav2Runtime(...)
  -> NormalSystemE2E.execute()
       -> create mission_id and trace_id
       -> world.start()
       -> BoundedGazeboNav2Runtime.start()
       -> world.bootstrap_localization()
       -> BoundedGazeboNav2Runtime.bootstrap_localization()
       -> construct mission request and request_id
       -> navigation/VLA-surrogate/verification requests
       -> live Gazebo world and structured-time observation
       -> world.close()
  -> run_sim008_qualification() extracts correlation/time/authority
```

### 3.3 SIM-009 L1-NAV graph

```text
run_sim009_qualification()
  -> run_failure_suite()
       -> GoalTrackedGazeboNav2Runtime()
            -> BoundedGazeboNav2Runtime.__init__()
       -> live_runtime.start()
       -> GoalTrackedGazeboNav2Runtime.bootstrap_localization()
            -> BoundedGazeboNav2Runtime.bootstrap_localization()
            -> _preflight_private_action_client()
                 -> _client()
                 -> rclpy.init() using temporary process-global ROS_DOMAIN_ID
       -> except Exception: live_ready=False          [cause discarded]
       -> _navigation_scenario()
            -> if not runtime.ready: return unavailable before request
            -> otherwise begin_scenario()
            -> _action_request() creates mission/request/trace/action IDs
            -> NavigationBackend.execute()
            -> GoalTrackedGazeboNav2Runtime.navigate()
            -> evidence_for(scenario_execution_id)
       -> sidecar run-local observation
       -> live_runtime.close()
  -> adapter normalizes every suite row
  -> collector validates selected required scenario
```

### 3.4 Shared-runtime answer

SIM-008 and SIM-009 share the runtime **PARTIALLY**.

Shared:

- `BoundedGazeboNav2Runtime` construction;
- ROS setup materialization;
- per-instance DDS domain, Gazebo partition, and log directory;
- launch command and process ownership;
- clock, odometry, AMCL initial pose, TF, and CLI action readiness;
- structured readiness measurements and cleanup.

Not shared:

- the wrapper/session owner (`NormalSystemE2E` versus `run_failure_suite`);
- runtime configuration ownership and timeout selection;
- initial-pose authority construction;
- private action-client readiness;
- exception and startup-failure representation;
- request/correlation lifecycle;
- result-envelope construction and canonical invocation frequency.

## 4. Runtime Authority Inventory

| Responsibility | Current authority | Other path / duplication | Classification |
| --- | --- | --- | --- |
| ROS installation environment | `ros_runtime_environment()` | Parent environment is still passed as an implicit base | `IMPLICIT_ENVIRONMENT` |
| ROS domain | `BoundedGazeboNav2Runtime.__init__()` | `_client()` temporarily mutates `os.environ["ROS_DOMAIN_ID"]` | `HIDDEN_SHARED_STATE` |
| Gazebo partition | `BoundedGazeboNav2Runtime.__init__()` | No second generator; inherited by subprocess probes | `SINGLE_AUTHORITY` |
| ROS log directory | `BoundedGazeboNav2Runtime.__init__()` | No second owner | `SINGLE_AUTHORITY` |
| World path | Runtime constructor | SIM-008 supplies scenario world; SIM-009 relies on default SIM-004 world | `CALL_PATH_DIVERGENCE` |
| Initial pose | Runtime instance for AMCL | launch arguments still use module `CANONICAL_START`; SIM-008 separately derives an instance pose | `DUPLICATED` |
| Startup/execution/cleanup bounds | Module globals in `run_simulation_navigation` | `GazeboSystemWorld.__init__()` writes them; SIM-009 reads the changed base behavior | `HIDDEN_SHARED_STATE` |
| SIM-009 scenario budgets | Constants in `failure_recovery` | Formerly derived at import time from mutable execution global; now locally fixed | `SINGLE_AUTHORITY` after repair |
| Gazebo/Nav2 launch | `BoundedGazeboNav2Runtime.start()` | Called by two independent session orchestrators | `DUPLICATED` orchestration |
| Process group ownership/cleanup | Runtime instance | Each repeated supplier call creates a fresh independent owner | `SINGLE_AUTHORITY`, over-invoked |
| Clock/odom/localization/action CLI readiness | Base runtime bootstrap | SIM-009 adds private rclpy action readiness | `CALL_PATH_DIVERGENCE` |
| Private Nav2 client | `GoalTrackedGazeboNav2Runtime._client()` | Uses rclpy default context and process-global environment mutation | `HIDDEN_SHARED_STATE` |
| Navigation request identity | `NormalSystemE2E._request()` / `failure_recovery._action_request()` | Separate task-specific creators | `DUPLICATED` |
| SIM-009 scenario execution identity | `begin_scenario()` | Created only after readiness succeeds | `CALL_PATH_DIVERGENCE` |
| Structured simulation time | SIM-008 world observation / SIM-009 sidecar | Different observation boundaries over the same Gazebo session type | `DUPLICATED` collection |
| Accepted binding verification | `resolve_predecessor_binding()` in active MIN-Q01 paths | Frozen maps and a legacy standalone `_binding()` remain; SIM-010 has its own immutable resolver | `DUPLICATED` repository authority surface |

The important distinction is that the low-level base runtime is substantially
shared, but no immutable object owns the entire run configuration and session
lifecycle. Sharing a class is not the same as sharing a canonical runtime
context.

## 5. Cross-Task State Audit

| State | Owner/writer | Reader | Proven effect |
| --- | --- | --- | --- |
| `STARTUP_SECONDS` | module default; overwritten by `GazeboSystemWorld.__init__()` from 45 to 20 | every later base `start()` | SIM-009 created after SIM-008 receives SIM-008's startup window |
| `EXECUTION_SECONDS` | module default; overwritten from 30 to 20 | base CLI navigation; formerly imported by SIM-009 policy | Already caused accepted 33-second manifest rejection; policy import was repaired, global remains mutable |
| `CLEANUP_SECONDS` | module default; overwritten to 5 | every later base `close()` | Cross-task ownership remains even though value currently equals default |
| `LOCALIZATION_SECONDS` | module constant | both base bootstraps | No current writer found; stable |
| `ROS_DOMAIN_ID` in runtime environment | per runtime instance | launch and subprocess probes | Fresh and isolated |
| `os.environ["ROS_DOMAIN_ID"]` | SIM-009 `_client()` temporarily writes/restores | rclpy default-context initialization and any concurrent process code | Process-global mutation is real; concurrent access and exceptional/repeated initialization remain implicit |
| rclpy default context | `rclpy.init()` / `rclpy.shutdown()` | every SIM-009 runtime in interpreter | Repeated canonical supplier calls rely on correct global teardown; no canonical repeatability gate proves it |
| DDS/Gazebo discovery cache | per-run domain/partition; CLI daemon disabled | launch/probes | Recent repair prevents known stale graph reuse |
| process ownership | runtime instance | `close()` | Recent repair captures descendant groups; canonical over-invocation multiplies cleanup boundaries |
| scenario/goal caches | `GoalTrackedGazeboNav2Runtime` instance | scenario evidence | Instance-local, filtered by scenario execution ID |
| canonical adapter output | subject loop | collector | SIM-009 full-suite output is regenerated ten times rather than retained once |

Cross-task mutable state is therefore **PRESENT**. The budget defect proved
that import/runtime order already changed SIM-009 behavior. The remaining
timeout writes and default rclpy context mean the class of defect has not been
removed, even though the known budget symptom was repaired.

The reverse direction is less direct: SIM-009 does not write the navigation
timeout globals, but its default rclpy context and temporary process-global
domain mutation can affect a later SIM-009 or other rclpy user in the same
interpreter if initialization or shutdown is incomplete. No current test proves
a later SIM-008 failure from SIM-009, because SIM-008 uses CLI clients rather
than rclpy; the risk is repeatability, not a proven reverse timeout mutation.

## 6. SIM-008 vs SIM-009 Bootstrap Comparison

| Stage | SIM-008 | SIM-009 L1-NAV |
| --- | --- | --- |
| ENV | Base runtime materializes Jazzy env and per-run isolation | Same base implementation |
| LAUNCH | Base `start()` | Same base implementation |
| CLOCK | Base localization bootstrap | Same base implementation |
| ODOM | Base topics and `odom -> base_link` checks | Same base implementation |
| LOCALIZATION | Scenario-derived AMCL pose, base lifecycle/TF checks | Default `CANONICAL_START`, base lifecycle/TF checks |
| ACTION | Base CLI `/navigate_to_pose` readiness | Base CLI readiness **plus** private rclpy client readiness |
| REQUEST | SIM-008 mission/trace exist before startup; request created after readiness | No scenario/request identity until after all readiness succeeds |
| OBSERVATION | World snapshot/time inside mission steps | Per-scenario result plus sidecar clock; infrastructure failure can still reach sidecar |
| CLEANUP | `NormalSystemE2E.finally` calls one runtime close | `run_failure_suite.finally` calls close, but exact bootstrap failure was discarded |

The first code-path divergence after the shared working bootstrap is the
SIM-009-only `_preflight_private_action_client()`. It initializes a private
rclpy client through the process-global default context and a temporary
`os.environ` mutation. However, the current suite discards all exceptions from
both the shared bootstrap and this extra preflight:

```python
try:
    live_runtime.start()
    live_ready = live_runtime.bootstrap_localization()
except Exception:
    live_ready = False
```

Consequently repository evidence cannot distinguish whether the latest run
failed in shared clock/localization readiness, in the private client preflight,
or by exception. The first *observable* divergence is the SIM-009-only private
preflight; the exact substep of the last live failure is deliberately erased by
the current result contract. This observability loss is itself part of the
architecture defect and is why another local fix cannot be responsibly chosen
from the current exception.

Bootstrap paths are classified **PRESENT** as duplicates at the session
orchestration level: localization code is inherited, but SIM-008 and SIM-009
independently create, configure, start, interpret, and clean the session, with
different extra readiness and error behavior.

## 7. Correlation Lifecycle

### Current creation points

- SIM-008 creates `mission_id` and `trace_id` at the beginning of
  `NormalSystemE2E.execute()`, before runtime startup. Its `request_id` is
  created when the mission request is built after readiness; on pre-request
  failure the exception path creates that request before returning a structured
  mission failure.
- SIM-009 assigns `qualification_run_id` only in the Q01 adapter after the
  suite row exists. It creates a `ScenarioExecution` only after the early
  `runtime.ready` guard. It creates mission/request/trace/action IDs in
  `_action_request()`, also after readiness.
- Therefore a SIM-009 readiness failure has a known manifest scenario but no
  actual request identity. The adapter cannot truthfully supply request
  correlation from `{"result", "error"}`.

### Judgment

`MISSING_RUN_LOCAL_CORRELATION` is primarily **A: a valid validator finding
caused by upstream runtime failure**. It also reveals a lifecycle/observability
weakness: qualification-attempt and scenario-execution identity are not created
before startup, so the structured infrastructure failure cannot be associated
with a canonical attempt independently of mission/request identity.

This is **not** a correlation-contract defect. Required SIM-009 operation
subjects still need actual same-run mission/request/trace identity. A runtime
that failed before request dispatch did not complete that subject and must
BLOCK MIN-Q01.

The converged model must distinguish:

```text
qualification/scenario attempt identity   created before runtime startup
mission/request/trace/action identity      created atomically with real request
pre-request infrastructure failure         structured BLOCKED, no fabricated request IDs
scenario semantic failure                  valid subject only after real request/observation
```

## 8. Provenance Authority Audit

For active MIN-Q01 paths, `resolve_predecessor_binding()` is now the sole
function that authenticates predecessor Evidence bytes:

```text
Acceptance -> accepted_commit -> git blob -> SHA-256 -> task/result
```

`failure_recovery._accepted_binding()` delegates to it. No remaining active
MIN-Q01 consumer was found reading accepted Evidence bytes from the mutable
`ROOT/results/simulation/...` path.

The repository authority surface is nevertheless still duplicated:

- `FROZEN` in the canonical runner and `ACCEPTED_PREDECESSOR_BINDINGS` in
  `failure_recovery` duplicate binding metadata.
- standalone SIM-008 `_binding()` serializes current Acceptance records without
  invoking the canonical resolver. It does not currently read Evidence bytes,
  but it is a second, weaker binding representation.
- frozen SIM-010 `observability_regression.resolve_accepted_evidence()` is a
  separate immutable-Git resolver. It is outside this task's modification
  boundary and must remain protected until the declared SIM-010 resume point.

Accordingly `duplicate_provenance_authority` is **PRESENT** at repository
architecture level, while the previously failing current-worktree authority
leak is absent from the active MIN-Q01 path.

The correction must centralize Q01's binding metadata and route all Q01
producers through `resolve_predecessor_binding()` without modifying accepted
artifacts or the frozen SIM-010 implementation.

## 9. Integration-Gate Audit

Current tests separately prove many leaf behaviors:

- immutable Git binding and hash failures;
- manifest budgets and scenario semantics with scripted runtimes;
- base localization sequence with controlled probes;
- private action-client preflight in isolation;
- process-group cleanup selection;
- task-specific adapter normalization and collector validation;
- controlled canonical routing.

They do **not** presently prove these boundaries in sequence:

| Desired gate | Current coverage |
| --- | --- |
| `RUNTIME_ENVIRONMENT_READY` | environment fields unit-tested; live SIM-008 previously observed |
| `RUNTIME_PROCESS_READY` | cleanup/process ownership unit-tested; no reusable shared-session contract |
| `NAVIGATION_READY` | SIM-008 live observed; SIM-009 private client only unit-tested |
| `CORRELATION_READY` | controlled result fixtures; no live SIM-009 request gate |
| `PROVENANCE_READY` | collectors tested with supplied rows; no live suite-to-collector gate |
| `CANONICAL_AGGREGATE_READY` | controlled partial routing; no complete 11-subject live gate |
| repeatability | classification helper exists; no back-to-back canonical/session gate |

The focused suite executed during this diagnosis passed:

```text
101 passed in 3.21s
```

This confirms the gap: all current unit/controlled scenario tests can pass
while live SIM-009 bootstrap/correlation and canonical aggregation remain
blocked. The full canonical preflight has been acting as the first integration
test for too many independent responsibilities.

## 10. Root Architecture Diagnosis

```yaml
primary_architecture_root_cause: COMBINED_RUNTIME_CONTEXT_DEFECT
secondary_contributors:
  - LATE_INTEGRATION_GATE_ARCHITECTURE
  - DUPLICATED_BOOTSTRAP_IMPLEMENTATION
  - CROSS_TASK_MUTABLE_STATE_ARCHITECTURE
blocker_sequence_classification: BOTH
```

The primary defect is not merely that two functions exist. It is that no
single immutable runtime context owns environment, bounds, isolation,
processes, bootstrap state, failure diagnostics, and request lifecycle from
construction through cleanup. Those responsibilities are assembled differently
by SIM-008, SIM-009, and the canonical subject loop.

The result is systemic architectural fragmentation:

- module globals make one task configure another;
- private client setup falls outside the common session contract;
- an exception becomes a boolean and loses its causal step;
- identities are created at incompatible lifecycle boundaries;
- one whole-suite supplier is invoked per subject rather than per canonical
  task execution;
- controlled tests stop before the first shared live integration boundary.

## 11. Converged Target Design

The smallest consolidation should reuse the existing runtime rather than
replace it.

### Immutable runtime configuration/context

Extend the existing navigation runtime with an immutable per-run configuration
containing:

- world and authoritative initial pose;
- startup, localization, execution, and cleanup bounds;
- materialized ROS installation environment;
- per-run DDS domain, Gazebo partition, ROS log directory;
- process ownership and cleanup measurements.

No constructor may write module timeout globals. Every subprocess and client
must receive the same context explicitly.

### One navigation session lifecycle

Make one existing base session own:

```text
launch -> clock -> odom -> localization -> action readiness -> cleanup
```

SIM-009 may add goal tracking and fault injection, but its private action
client must join the same explicit context and return a structured readiness
stage/result. Use an explicit rclpy `Context`/domain rather than temporarily
mutating process-global `os.environ`.

### Explicit identity phases

Create qualification-attempt and scenario-execution identity before startup.
Create mission/request/trace/action identity only with an actual request. A
pre-request failure becomes an explicit execution-integrity BLOCKED envelope
carrying the attempt/scenario identity and exact readiness failure, not a fake
scenario-semantic result.

### One adapter invocation per task execution

The canonical runner must invoke the SIM-009 supplier once, retain its mapping
of explicitly keyed scenario results, and route the ten required subjects from
that mapping. Each row remains independently bound by scenario execution ID;
the suite itself is not re-executed ten times.

### Canonical accepted binding resolver

Keep `resolve_predecessor_binding()` as Q01's only Evidence verifier and use one
frozen binding table. Remove Q01-local alternate binding representations from
execution-result construction. Do not modify frozen SIM-010 in this correction.

## 12. Chosen Correction Boundary

```yaml
recommended_correction: RUNTIME_CONTEXT_AND_IDENTITY_CONSOLIDATION_REQUIRED
architecture_change_required: YES
scope_contract_change_required: NO
```

The change is an internal architecture consolidation, not a reopening of the
frozen 11-subject MIN-Q01 contract.

Modules to change:

- `scripts/run_simulation_navigation.py`
- `scripts/run_simulation_normal_system_e2e.py`
- `scripts/sim009_goal_tracked_navigation.py`
- `src/simulation_runtime/failure_recovery.py`
- `scripts/q01_execution_adapters.py`
- `scripts/run_simulation_provenance_qualification.py`
- narrowly related tests in the four existing simulation test files

Responsibilities to centralize:

- immutable runtime bounds/environment/isolation/process ownership;
- shared readiness stages and diagnostic result;
- explicit rclpy client context;
- qualification/scenario attempt identity versus request correlation;
- one SIM-009 suite execution per canonical run;
- Q01 accepted-binding metadata and resolution.

Protected modules/artifacts:

- accepted SIM-004/005/007/008/009 Acceptance and Evidence;
- frozen accepted commits;
- `tasks/TASK-SIM-Q01-MIN.md` and its 11-subject manifest;
- frozen SIM-010 implementation and state;
- protected dirty SIM-004 worktree Evidence;
- task-specific accepted semantic oracles and collector validation rules.

## 13. Bounded Implementation Plan

### Task 1 — Make runtime context immutable

**Goal:** Replace module-global runtime configuration with a per-instance
configuration/context used by launch, probes, navigation, and cleanup.

**Files/symbols:** `scripts/run_simulation_navigation.py`;
`BoundedGazeboNav2Runtime`, timeout reads, environment construction, launch
pose arguments.

**Invariant established:** Constructing SIM-008 cannot change a later SIM-009
runtime; the launch pose and AMCL pose come from the same authoritative config;
ROS environment and isolation are explicit and instance-local.

**Tests:** two runtimes with different bounds/poses remain independent; exact
environment is inherited by launch/probes; no module global changes; unrelated
process groups are never targeted.

**Stop condition:** Any required behavior depends on mutating a shared module
global or parent `os.environ`.

### Task 2 — Converge SIM-008/SIM-009 navigation sessions

**Goal:** Make both paths use the same readiness/session result and preserve the
first failed readiness stage.

**Files/symbols:** `scripts/run_simulation_normal_system_e2e.py`,
`scripts/sim009_goal_tracked_navigation.py`,
`src/simulation_runtime/failure_recovery.py`.

**Invariant established:** SIM-009 reaches the same launch/clock/odom/AMCL/TF/
action gate as SIM-008; its private client uses an explicit rclpy context; a
failure retains exact stage/error and is not collapsed to an unexplained bool.

**Tests:** shared readiness sequence for both callers; private-client discovery
on the runtime domain; startup exception retained; cleanup after every failed
stage; no stale graph on a second session.

**Stop condition:** A SIM-009 requirement cannot be represented as an additive
capability over the shared session without changing accepted semantics.

### Task 3 — Separate attempt identity from request correlation

**Goal:** Represent pre-request infrastructure failure truthfully while
preserving required same-run correlation for completed operation subjects.

**Files/symbols:** `failure_recovery._navigation_scenario`,
`GoalTrackedGazeboNav2Runtime.begin_scenario`, `_action_request`,
`run_sim009_qualification`, `collect_sim009_execution_result` boundary.

**Invariant established:** qualification/scenario attempts always have an
identity; mission/request/trace/action IDs exist only for a real request; a
pre-request readiness failure blocks before subject construction; no identifier
is fabricated after failure.

**Tests:** live-ready path preserves exact same-run IDs; pre-request failure
produces structured integrity BLOCKED with no request IDs; collector still
rejects a required subject lacking actual correlation.

**Stop condition:** Passing the gate would require relaxing correlation or
manufacturing request identity.

### Task 4 — Execute each canonical supplier once and retain one authority path

**Goal:** Invoke SIM-008 once and SIM-009 once per canonical attempt, then route
explicitly keyed results; use one Q01 immutable binding table/resolver.

**Files/symbols:** `collect_qualification_subjects`, `live_adapters`,
`run_sim009_qualification`, `FROZEN`, `ACCEPTED_PREDECESSOR_BINDINGS`, legacy
SIM-008 `_binding()` where reached by Q01.

**Invariant established:** one suite execution yields ten unique, scenario-bound
records; no row satisfies another scenario; mutable worktree Evidence never
becomes authority; SIM-008/SIM-009 bootstrap cannot be multiplied by subject
enumeration.

**Tests:** supplier call counts are exactly 1/1; missing/duplicate/cross-scenario
rows block; dirty worktree is irrelevant to accepted Git resolution.

**Stop condition:** any routing requires backend-name or list-position matching,
or a second accepted-Evidence verifier.

### Task 5 — Install staged live gates and repeatability

**Goal:** Verify each responsibility before invoking the canonical aggregate.

**Files/symbols:** existing navigation, normal-system, failure-recovery, and
provenance qualification test modules; no accepted artifacts.

**Invariant established:** each gate below passes independently, then two
back-to-back canonical/equivalent runs are free of stale process, DDS, Gazebo,
rclpy, and mutable-timeout dependence.

**Tests:** GATE-1 through GATE-7 below.

**Stop condition:** Gate N+1 is not run until Gate N passes, or the second run
observes an earlier process/graph/state.

## 14. Required Integration Gates

### GATE-1 — `STATIC_PROVENANCE`

- **Input:** frozen binding table, current Acceptance records, accepted Git
  commits/blobs.
- **Expected output:** verified commit/path/SHA/task/result for every required
  predecessor; dirty worktree independent.
- **Failure meaning:** provenance architecture defect; do not start runtime.

### GATE-2 — `RUNTIME_ENVIRONMENT`

- **Input:** one immutable runtime config/context.
- **Expected output:** materialized Jazzy environment, unique DDS domain/Gazebo
  partition/log directory, owned process registry, no module/global mutation.
- **Failure meaning:** runtime infrastructure/configuration defect.

### GATE-3 — `SIM008_RUNTIME`

- **Input:** canonical SIM-008 scenario and context.
- **Expected output:** launch, clock, odom, localization, action, mission,
  structured simulation time, bounded cleanup.
- **Failure meaning:** shared session or SIM-008 semantic adapter defect; do not
  run SIM-009.

### GATE-4 — `SIM009_NAVIGATION_RUNTIME`

- **Input:** one fresh shared navigation session with SIM-009 goal tracking.
- **Expected output:** private client ready and all four required NAV scenario
  executions produce explicitly keyed live results with exact failure/retry
  semantics and cleanup.
- **Failure meaning:** SIM-009 additive capability/bootstrap defect, reported by
  exact readiness stage; do not invoke collector/aggregate.

### GATE-5 — `SAME_RUN_CORRELATION`

- **Input:** GATE-4 request/result records.
- **Expected output:** mission/request/trace/action binding from each real
  request; retry identity rules preserved; pre-request failure represented only
  as execution-integrity BLOCKED.
- **Failure meaning:** identity lifecycle defect; never backfill IDs.

### GATE-6 — `CANONICAL_11_SUBJECT`

- **Input:** one SIM-008 result and one SIM-009 suite mapping.
- **Expected output:** exactly 11 valid subjects, no missing/extra/binding error,
  `SIM_PROVENANCE_QUALIFICATION_READY`.
- **Failure meaning:** adapter/collector/aggregator integration defect.

### GATE-7 — `REPEATABILITY`

- **Input:** cleanup from GATE-6 followed by a second canonical run, or an
  equivalent full live session sequence if Evidence writing is intentionally
  deferred.
- **Expected output:** semantically equivalent results, fresh run identities and
  isolation tokens, no surviving owned processes, no stale graph, no inherited
  timeout/context state.
- **Failure meaning:** runtime context or cleanup is still not authoritative.

Focused unit success is insufficient. Completion requires isolated SIM-008,
live SIM-009 navigation, same-run correlation, canonical 11-subject readiness,
and the repeatability gate.

## 15. Risks and Protected Scope

- Consolidation must not turn a pre-request infrastructure failure into an
  accepted scenario semantic failure.
- A shared session must retain SIM-009 fault injection and per-scenario goal
  evidence; sharing cannot permit cross-scenario result reuse.
- Caching the SIM-009 supplier output is per canonical attempt only. It must not
  survive into a later canonical run.
- Explicit rclpy contexts must be shut down before process cleanup completes.
- Immutable runtime config must preserve accepted scenario budgets, especially
  the 33-second timeout/retry scenario.
- No accepted predecessor artifact, frozen commit, MIN-Q01 subject, or SIM-010
  source is changed by the correction.
- The protected dirty SIM-004 result must remain untouched and non-authoritative.

No source, test, accepted Evidence, Acceptance, canonical Evidence, or
orchestrator state was modified during this diagnosis.

## 16. Final Decision

```yaml
primary_architecture_root_cause: COMBINED_RUNTIME_CONTEXT_DEFECT
blocker_sequence_classification: BOTH
sim008_sim009_runtime_shared: PARTIAL
cross_task_mutable_state: PRESENT
duplicate_bootstrap_paths: PRESENT
duplicate_provenance_authority: PRESENT
correlation_contract_defect: NO
recommended_correction: RUNTIME_CONTEXT_AND_IDENTITY_CONSOLIDATION_REQUIRED
architecture_change_required: YES
scope_contract_change_required: NO
implementation_ready: YES
```

The implementation is ready to proceed as one bounded convergence correction,
not another isolated `MISSING_RUN_LOCAL_CORRELATION` patch. The frozen MIN-Q01
scope remains exactly one SIM-008 plus ten SIM-009 subjects.
