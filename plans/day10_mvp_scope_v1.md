# Day-10 MVP Scope v1.0

> **Authoritative Day-10 scope source of truth.** Frozen after TASK-P0-002 Architecture Freeze and reconciled by TASK-P0-002R.  
> Scope invariant: **1 Mission + 1 Failure + 1 Recovery + Evidence**

## Canonical mission

`Line B에 Brake ECU Type-B 1개를 공급해줘.`

Fixture:

- part: `Brake ECU Type-B`
- quantity: `1`
- source: `Rack A19`
- destination: `Line B`

## Canonical normal path

```text
Operator
→ Factory Agent
→ Structured Mission
→ Deterministic Runtime
→ WMS Fake
→ Robot Skill Fake
→ COMPLETED
→ SQLite / machine-readable evidence
```

## Canonical single failure

First Robot Skill execution returns an ambiguous timeout.

```text
TIMEOUT
→ action UNKNOWN
→ mission RECONCILING
→ get_action_status
→ FAILED + retryable
→ RECOVERING
→ one retry
→ SUCCEEDED
→ COMPLETED
```

## Required evidence

- mission result
- tool-call validity
- state transitions
- timeout handling
- reconciliation
- retry budget/count
- recovery result
- HITL escalation flag
- mission duration
- mission/action correlation
- error category
- component versions

## Out of scope

- physical robot/camera
- VLA fine-tuning/inference
- real WMS/MES/PHM/Fleet
- real Nav2/MoveIt integration
- multi-agent
- PostgreSQL
- Docker Compose
- Grafana/Kubernetes
- custom navigation/motion/control/simulator
- extra failure scenarios

## Scope-change rule

Any request that introduces a second business mission, second failure scenario, physical hardware, VLA, or real ROS adapter is **not Day-10 MVP** and must be a separate task after MVP-008.
