# Simulation Smoke Runtime v1

> Task: `TASK-SIM-002`
> Implementation status: `COMPLETE`
> Task-specific decision: `SIM_SMOKE_READY`
> Independent acceptance: `PENDING`
> Downstream authorization: `TASK-SIM-GATE readiness eligibility = false`

## 1. Purpose and accepted predecessor

This report describes the smallest bounded deterministic executable proof of the accepted Simulation Contract Profile. The predecessor binding was verified before implementation:

| Accepted predecessor artifact | SHA-256 |
|---|---|
| `docs/simulation/simulation_contract_profile_v1.md` | `24e9dbdbccb34e4799a43a7a3bbef5f5ebbb84d211aa9506cdae567c238645e1` |
| `results/simulation/SIM-001_contract_profile.json` | `c7ea4be8b6e34bc5eff3ef15c728ac76cb34d280d5def3a73fdabb52c6ad642d` |
| SIM-001 canonical evidence payload | `2d00ad019c33a53e4b3bf83cc0217666ca5efb89196a386645ff36c4c6a58b4e` |
| `results/reviews/SIM-001_acceptance.json` | `bf1fe8df30a73339fcdd90a5bbc3d0cf5963a0a02d538102e732054e175f5e53` |

The accepted SIM-001 reviewed commit is `97bef9208b26c9fef577e97c26f76a125f220ed9`. Its review decision is `ACCEPT`, its task-specific decision is `SIM_CONTRACT_PROFILE_READY`, and its acceptance record authorizes `TASK-SIM-002` only.

## 2. Executable boundary

The entry point is:

```text
scripts/run_simulation_smoke.py
```

The deterministic core is:

```text
src/simulation_runtime/smoke.py
```

It validates messages against the accepted closed Simulation Lane schema and enforces the semantic correlations required by the profile. It implements only the protocol-neutral logical operations:

```text
mission.execute
navigation.execute
vla.execute
action_status.get
verification.verify
```

It does not define ROS, HTTP, gRPC, Nav2, MoveIt, `ros2_control`, physical-device, or mission-to-actuator interfaces.

## 3. Scenario results

| Scenario | Executed behavior | Result | Bound |
|---|---|---|---|
| `S01` deterministic success | Navigation and VLA return contract-valid success; exact deterministic verification returns `pass`; Mission returns `completed`. | `PASS` | `1000 ms` |
| `S02` deterministic failure | Navigation returns `status=failed`, `result=failure`, `error.category=EXECUTION_FAILED`. | `PASS` | `1000 ms` |
| `S03` bounded timeout | A deterministic virtual no-result reaches its finite bound and returns `status=unknown`, `result=pending`, `error.category=MODEL_TIMEOUT`. | `PASS` | `1000 ms` |
| `S04` ambiguous/reconcile | Timeout remains `unknown`; matching `action_status.get` evidence drives `unknown -> reconciling -> reconciled(resolved_status=succeeded)`. | `PASS` | `1000 ms` |

Direct `unknown -> succeeded` is rejected. Reconciliation matches `mission_id`, `action_id`, lookup `request_id`, timestamped evidence, and component version before a resolved success is usable.

## 4. Determinism and boundedness

- Repeated executions return byte-equivalent canonical JSON with SHA-256 `7a7aff1014a03c02f76cbdd1909ce52e717e096c6128c121ec3dd1bc8518479a`.
- Requests, fixture content, identities, timestamps, deadlines, outcomes, and bounds are fixed.
- No random source, network call, business-decision wall clock, sleep, retry loop, background worker, or child process is used by the runtime.
- Timeout uses a deterministic virtual no-result at the declared bound rather than waiting on a real device or clock.
- Each scenario has `execution_bound_ms=1000`; retries performed are zero.
- Cleanup reports zero child processes, background workers, and temporary files, with `cleanup_complete=true`.

## 5. Fixture and verification integrity

All observations use `fixture_set_id=SIM_FIXTURE_SET_V1` and `source_kind=mock`. Fixture identity/version pairs resolve exactly once. The runtime compares fixture set, identity, version, content hash, timestamp, and source kind, and recomputes the canonical observation SHA-256 before use.

Verification uses `sim-exact-match-v1`:

```text
valid exact part_id/location_id match -> pass
valid mismatch -> fail
insufficient or ambiguous observation -> uncertain
```

`uncertain` cannot become `pass`, and verification does not independently commit mission completion.

## 6. Isolation and preserved authorization

- physical robot dependency: `false`
- physical camera dependency: `false`
- physical motion executed: `false`
- physical teleoperation dependency: `false`
- training/fine-tuning dependency: `false`
- Dataset V1 created: `false`
- Week authorization modified: `false`
- hardware target frozen: `false`
- `SIM_FIXTURE_SET_V1 != Dataset V1`
- historical `P0-004R = NO_GO` remains unchanged

Candidate myCobot, myAGV, D455, and Orin hardware is neither accessed nor frozen.

## 7. Validation

| Validation | Result |
|---|---|
| SIM-001 consumer eligibility reconstruction | `PASS` |
| Focused smoke tests | `11 passed` |
| Full regression | `169 passed` |
| AST/static parse | `PASS` |
| Repeated canonical output comparison | `PASS` |
| CLI completion under a 5-second external test bound | `PASS` |
| Physical/network/process static and runtime isolation | `PASS` |
| `git diff --check` | `PASS` |

## 8. State separation

```text
TASK-SIM-002 implementation: complete
Task-specific decision: SIM_SMOKE_READY
Independent acceptance: pending
TASK-SIM-GATE readiness eligibility: false
```

Implementation completion and `SIM_SMOKE_READY` do not authorize the gate, produce `SIM_GO`, modify Week authorization, or authorize physical, dataset, or training activity. A separate independent review and immutable post-review `SIM-002_acceptance.json` binding are required before `TASK-SIM-GATE` may consume this result as READY evidence.
