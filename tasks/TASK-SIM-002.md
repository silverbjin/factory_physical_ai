# TASK-SIM-002 — Deterministic Smoke Runtime

> Lane: Simulation
> Type: Minimal executable simulation proof
> Status: READY_FOR_IMPLEMENTATION only after accepted TASK-SIM-001
> Predecessor:
>
> * accepted `TASK-SIM-001`
>   Downstream:
> * `TASK-SIM-GATE`
>   Physical Authorization: NONE

---

# 1. Purpose

Implement the smallest bounded deterministic executable path necessary to prove that the accepted simulation contract profile can execute without physical hardware.

This task solves the gate circularity problem by creating executable evidence **before** `TASK-SIM-GATE`.

---

# 2. Goal

Demonstrate:

```text
authoritative simulation contract profile
        ↓
bounded deterministic fixture/runtime
        ↓
known input
        ↓
known result/failure/timeout
        ↓
machine-readable evidence
```

without:

* physical robot access;
* physical camera access;
* training;
* Dataset V1;
* Week task implementation.

---

# 3. Sources of Truth

Use:

* accepted `TASK-SIM-001` evidence;
* `simulation_contract_profile_v1.md`;
* governing architecture;
* existing runtime/state contracts;
* applicable accepted tests.

Do not introduce behavior outside the accepted profile.

---

# 4. Implementation Boundary

The smoke runtime shall sit behind existing boundaries such as:

```text
Navigation Skill
VLA Skill
Verification
```

and/or the current deterministic mission executor boundary as specified by SIM-001.

It shall not create a direct physical actuator contract.

---

# 5. Required Smoke Scenarios

At minimum implement deterministic scenarios for the behaviors supported by the accepted profile.

Recommended minimum:

## S01 — Deterministic Success

```text
known request
→ deterministic fixture
→ expected successful result
```

## S02 — Deterministic Failure

```text
known request
→ deterministic fixture
→ explicit failure result
```

## S03 — Bounded Timeout

```text
known request
→ controlled delay/no-result
→ bounded timeout
→ non-success
```

## S04 — Ambiguous / Unknown Outcome

When supported by the authoritative contract:

```text
ambiguous outcome
→ reconciliation / blocked completion
```

The task shall never convert ambiguous output directly into success if frozen semantics prohibit it.

---

# 6. Determinism Requirements

The runtime shall avoid:

* uncontrolled randomness;
* external physical dependencies;
* uncontrolled network dependency;
* wall-clock-dependent business decisions;
* unbounded retries;
* hidden global state.

Given the same fixture and initial state, the smoke scenario shall produce semantically equivalent outcomes.

---

# 7. Boundedness

Every smoke scenario shall have an explicit execution bound.

The runtime must not:

* wait forever;
* leave child processes running;
* leave simulator processes running;
* leak queues/files;
* retry indefinitely.

---

# 8. Physical Isolation

Static and runtime evidence must establish that the smoke path does not require:

```text
/dev/tty*
/dev/video*
robot controller
physical camera
physical gripper
physical E-stop
```

Physical execution remains unauthorized.

---

# 9. Training Isolation

The smoke runtime shall not require:

* model fine-tuning;
* optimizer execution;
* remote training compute;
* Dataset V1.

VLA behavior may be represented by an accepted deterministic fixture if allowed by SIM-001.

---

# 10. Simulation Fixture Naming

Use simulation-specific identifiers such as:

```text
SIM_FIXTURE_SET_V1
```

Do not generate or claim:

```text
Dataset V1
```

---

# 11. Required Artifacts

## Executable Smoke Entry Point

Example path:

```text
scripts/run_simulation_smoke.py
```

or repository-consistent equivalent.

## Tests

Example:

```text
tests/test_simulation_smoke.py
```

## Evidence

```text
results/simulation/SIM-002_smoke_runtime.json
```

## Human-readable Report

```text
docs/simulation/simulation_smoke_runtime_v1.md
```

## Task History

According to repository task-history conventions.

---

# 12. Minimum Evidence

Record:

```text
task identity
accepted SIM-001 source binding
scenario identities
execution bounds
results
failure semantics
timeout result
physical dependency status
training dependency status
Week authorization unchanged
source hashes
decision
```

---

# 13. Checks

```text
C01 Accepted SIM-001 evidence bound
C02 Smoke entry point exists
C03 Success scenario passes
C04 Failure scenario behaves correctly
C05 Timeout is bounded
C06 Unknown/reconcile behavior correct where applicable
C07 Determinism verified
C08 No physical robot dependency
C09 No physical camera dependency
C10 No physical motion
C11 No training dependency
C12 No Dataset V1 produced
C13 No W-task authorization changed
C14 No new incompatible public contract introduced
C15 Runtime cleanup PASS
C16 Focused tests PASS
C17 Regression PASS
C18 Evidence consistent
```

---

# 14. Decision

Return exactly:

```text
SIM_SMOKE_READY
```

or:

```text
SIM_SMOKE_BLOCKED
```

`SIM_SMOKE_READY` means there is now actual bounded executable evidence that the Simulation Lane can execute through the accepted profile.

It does not authorize downstream simulation work by itself.

That authorization belongs to `TASK-SIM-GATE`.

---

# 15. Out of Scope

Do not:

* implement full simulator behavior;
* implement physical adapters;
* modify Week task graph;
* change P0-004R authorization;
* access real hardware;
* train models;
* create Dataset V1;
* provision paid resources.

---

# 16. Independent Review

A separate read-only review shall verify:

* accepted SIM-001 binding;
* deterministic behavior;
* timeout boundedness;
* physical independence;
* no contract leakage;
* no W-task authorization mutation;
* evidence integrity.

Only accepted:

```text
SIM_SMOKE_READY
```

may be consumed by `TASK-SIM-GATE`.

---

# 17. Final Status

Report separately:

```text
TASK-SIM-002 implementation complete/incomplete

SIM_SMOKE_READY
or
SIM_SMOKE_BLOCKED

Independent acceptance:
pending
```
