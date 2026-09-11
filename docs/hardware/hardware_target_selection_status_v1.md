# Hardware Target Selection Status v1

> Status: INFORMATIONAL / NOT FROZEN
> Purpose: Record owned/candidate hardware without superseding existing architecture decisions.
> Governing Sources:
>
> * ADR-001
> * ADR-002
> * ADR-005
> * ADR-010
> * accepted P0-006 evidence

---

# 1. Purpose

Record hardware currently available or preferred for future physical integration while preserving the authoritative status of existing architecture decisions.

This document is not a hardware freeze.

It does not change any unresolved target-selection decision already recorded by accepted ADRs or readiness evidence.

---

# 2. Core Distinction

The project distinguishes:

```text
OWNED_HARDWARE
CANDIDATE_HARDWARE
ARCHITECTURALLY_SELECTED
OPERATIONALLY_READY
PHYSICALLY_AUTHORIZED
```

These states are not interchangeable.

Example:

```text
myCobot 280 Pi

Owned:
provenance

Candidate:
YES

Architecturally selected:
NO / unresolved under current ADR

Operationally ready:
NOT_VERIFIED

Physical motion authorized:
NO
```

---

# 3. Manipulator Status

Candidate / owned hardware:

```text
myCobot 280 Pi
```

Current architectural authority:

```text
ADR-001
```

Current status:

```text
CANDIDATE_HARDWARE
NOT_ARCHITECTURALLY_FROZEN
```

This document shall not override ADR-001's existing selection/defer logic.

Future selection of myCobot 280 Pi as the official physical target requires an explicit architecture change decision.

---

# 4. AMR Status

Candidate / owned hardware:

```text
myAGV JN 2023
```

Current architectural authority:

```text
ADR-002
```

Current status:

```text
CANDIDATE_HARDWARE
NOT_ARCHITECTURALLY_FROZEN
```

Final AMR selection remains deferred under the current authority.

---

# 5. Camera Status

Candidate / owned hardware:

```text
Intel RealSense D455
```

Current architectural authority:

```text
ADR-005
```

Current V1 observation contract shall remain whatever ADR-005 currently defines.

The existence of D455 hardware does not silently upgrade the project to a frozen RGB-D contract.

Current status:

```text
CANDIDATE_HARDWARE
NOT_ARCHITECTURALLY_FROZEN
```

A future RGB-D contract change must explicitly amend/supersede the applicable camera ADR.

---

# 6. Edge Compute Status

Candidate / owned hardware:

```text
Jetson Orin Nano
```

Current architectural authority:

```text
ADR-010
```

Current status:

```text
CANDIDATE_HARDWARE
DEPLOYMENT_ROLE_NOT_FROZEN
```

Actual deployment ownership and workload placement remain governed by later evidence and architecture decisions.

---

# 7. Development Host

Development host facts may be referenced from accepted P0 evidence.

The development host is not automatically the production deployment target.

Training-resource classification remains governed separately.

---

# 8. Accepted P0-006 Historical Evidence

Accepted P0-006 evidence may record:

```text
target selection = unresolved
camera selection = unresolved
```

This remains valid historical evidence.

A future architecture decision may change the target-selection state, but must not rewrite historical P0-006 evidence.

---

# 9. Simulation Implication

The Simulation Lane does not require final physical target selection.

It targets the project-facing skill/verification contract boundaries.

Therefore deterministic simulation fixtures shall not depend on:

```text
myCobot-specific commands
myAGV-specific protocol
D455-specific device API
Orin-specific deployment API
```

unless a future task explicitly introduces such dependence after the relevant architecture decision.

---

# 10. Future Hardware Selection Process

Final target selection shall follow:

```text
Candidate Inventory
        ↓
Suitability / Compatibility Evidence
        ↓
TASK-HW-SELECT-*
        ↓
Architecture Change Proposal
        ↓
ADR Amendment / Supersession
        ↓
Independent Architecture Review
        ↓
ACCEPT
        ↓
Hardware Target Freeze
```

---

# 11. Required Selection Evidence

A future final target selection should evaluate at least:

## Manipulator

* supported control path;
* state feedback;
* gripper compatibility;
* simulator compatibility;
* workspace;
* safety/abort path;
* VLA skill integration impact.

## AMR

* navigation stack compatibility;
* state/control ownership;
* simulation counterpart;
* recovery semantics;
* deployment topology.

## Camera

* observation contract;
* RGB/RGB-D requirements;
* timing;
* resolution;
* calibration;
* simulator correspondence.

## Edge Compute

* runtime compatibility;
* memory;
* performance;
* deployment ownership;
* networking;
* artifact packaging.

---

# 12. Current Status Summary

| Category     | Candidate        | Architectural Status                            | Physical Readiness |
| ------------ | ---------------- | ----------------------------------------------- | ------------------ |
| Manipulator  | myCobot 280 Pi   | unresolved / not frozen                         | not verified       |
| AMR          | myAGV JN 2023    | unresolved / not frozen                         | not verified       |
| Camera       | RealSense D455   | unresolved / existing camera contract preserved | not verified       |
| Edge compute | Jetson Orin Nano | deployment target unresolved                    | not verified       |

---

# 13. Invariants

```text
Candidate != Selected

Selected != Ready

Ready != Motion Authorized

Owned hardware != Frozen architecture
```

---

# 14. Change Control

This informational document may be updated as hardware inventory changes.

It shall not be used as authority to supersede ADR-001/002/005/010.

Only an explicitly accepted architectural change may freeze final physical targets.


