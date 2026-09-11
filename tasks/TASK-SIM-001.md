# TASK-SIM-001 — Simulation Contract Profile

> Lane: Simulation
> Type: Contract-profile / Architecture-readiness task
> Status: READY_FOR_IMPLEMENTATION after Simulation Lane ADR freeze
> Predecessor:
>
> * `ADR-Simulation-Lane-v1.md`
>   Downstream:
> * `TASK-SIM-002`
>   Physical Authorization: NONE

---

# 1. Purpose

Define the exact existing architecture/contract surface that the Simulation Lane is allowed to emulate.

This task shall answer:

> "Which existing project-facing boundaries must a deterministic simulation fixture implement so that later simulation execution can validate software behavior without introducing new actuator ownership?"

---

# 2. Scope

The task shall inspect and profile the applicable existing boundaries, including when relevant:

```text
Deterministic Mission Executor
Navigation Skill boundary
VLA Skill boundary
Verification boundary
```

The task shall not create a direct actuator contract.

---

# 3. Sources of Truth

Inspect:

* applicable architecture documents;
* current system architecture;
* contract plan;
* applicable ADRs;
* accepted Phase 0 evidence;
* existing state/reconciliation semantics;
* applicable tests.

If the contract plan is planning-only and lacks executable APIs, record that fact explicitly.

Do not pretend that a planning contract is already an executable interface.

---

# 4. Required Output

Create:

```text
docs/simulation/simulation_contract_profile_v1.md
```

and optionally machine-readable evidence:

```text
results/simulation/SIM-001_contract_profile.json
```

according to repository conventions.

---

# 5. Contract Profile Content

At minimum classify:

## Mission Executor Boundary

* invocation semantics;
* required state;
* action lifecycle;
* success/failure representation;
* reconciliation relationship.

## Navigation Skill Boundary

* request concept;
* result concept;
* failure concept;
* timeout behavior;
* ownership.

## VLA Skill Boundary

* request concept;
* skill/action result concept;
* prohibited direct actuator ownership;
* uncertainty/failure behavior;
* authorization boundary.

## Verification Boundary

* observation/result verification;
* expected/actual state;
* success/reconcile/escalate semantics where applicable.

---

# 6. Executable Contract Status

For each boundary classify:

```text
EXECUTABLE_CONTRACT_AVAILABLE
PLANNING_CONTRACT_ONLY
PARTIALLY_DEFINED
NOT_DEFINED
```

No status may be upgraded merely because future simulation needs it.

---

# 7. Fixture Profile

For each applicable boundary define the minimum deterministic fixture semantics needed by `TASK-SIM-002`.

Examples:

```text
known request
→ known deterministic success

known request
→ deterministic timeout

known request
→ deterministic failure

ambiguous result
→ reconciliation / non-success
```

The fixture profile describes behavior.

It does not yet implement the behavior.

---

# 8. Physical Exclusions

The profile must explicitly exclude:

* real robot device access;
* real camera access;
* physical motion;
* physical gripper commands;
* physical teleoperation;
* physical E-stop execution;
* vendor-specific hardware dependency.

---

# 9. Dataset Boundary

Simulation fixtures may carry deterministic observations.

They shall be identified as:

```text
SIM_FIXTURE_SET_V1
```

or equivalent.

They shall not be called:

```text
Dataset V1
```

unless the authoritative Week task explicitly owns and creates that artifact.

---

# 10. Training Boundary

The profile may emulate VLA skill output.

It shall not require actual SmolVLA fine-tuning.

Actual training remains separately gated.

---

# 11. No New Lower-level Port

Do not introduce:

```text
ManipulatorPort
NavigationPort
ObservationPort
```

as frozen public architecture merely to simplify simulation.

If a lower-level abstraction is necessary, stop and report a contract-gap finding.

That requires a separate contract/ADR change before this task can complete.

---

# 12. Required Checks

```text
C01 Governing Simulation ADR frozen
C02 Existing architecture located
C03 Mission execution boundary identified
C04 Navigation Skill boundary classified
C05 VLA Skill boundary classified
C06 Verification boundary classified
C07 Executable/planning status truthful
C08 Direct actuator ownership absent
C09 Deterministic fixture semantics defined
C10 Failure path defined
C11 Timeout behavior defined
C12 Reconciliation relationship defined where applicable
C13 Physical dependency absent
C14 Dataset V1 not aliased
C15 Training not required
C16 No Week task authorization changed
C17 No existing contract silently rewritten
C18 Output internally consistent
```

---

# 13. Decision

Return one:

```text
SIM_CONTRACT_PROFILE_READY
SIM_CONTRACT_PROFILE_BLOCKED
```

READY means sufficient contract semantics exist for `TASK-SIM-002` to implement a bounded deterministic smoke path without inventing an incompatible architecture.

BLOCKED means required simulation semantics cannot yet be implemented safely from the authoritative sources.

---

# 14. Important BLOCKED Example

If the project contains only:

```text
"VLA Skill exists"
```

but no sufficiently precise executable request/result semantics for the smoke runtime, do not invent them.

Return:

```text
SIM_CONTRACT_PROFILE_BLOCKED
```

and identify the exact contract gap.

---

# 15. Out of Scope

Do not:

* implement simulation fixtures;
* implement smoke runtime;
* run physical hardware;
* modify Week task mapping;
* change P0-004R;
* freeze hardware selection;
* train a model;
* collect Dataset V1.

---

# 16. Independent Review

A separate read-only review must verify:

* source authority;
* no invented executable contract;
* consistency with frozen architecture;
* absence of actuator ownership;
* dataset distinction;
* physical isolation;
* profile sufficiency for SIM-002.

Only accepted `SIM_CONTRACT_PROFILE_READY` evidence may be consumed by `TASK-SIM-002`.

---

# 17. Final Status

Implementation report shall distinguish:

```text
TASK-SIM-001 implementation complete/incomplete

SIM_CONTRACT_PROFILE_READY
or
SIM_CONTRACT_PROFILE_BLOCKED

Independent acceptance:
pending
```