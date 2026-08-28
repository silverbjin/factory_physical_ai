# TASK-MVP-003 — Deterministic Tool Gateway and Fakes

> Status: READY FOR EXECUTION
> Phase: Day-10 MVP
> Architecture prerequisite: TASK-P0-002 = GO
> Physical robot authorized: NO
> VLA runtime/fine-tuning required: NO
> Scope invariant: 1 Mission + 1 Failure + 1 Recovery + Evidence


## 1. Goal

Implement one in-process deterministic factory-tool gateway and the minimum fakes required for the canonical mission.

The MVP must not create WMS, Fleet, PHM, Navigation, VLA, and Verification as separate services.

## 2. Required fake capabilities

### Factory/WMS Fake

Support only what the canonical mission needs:

```text
query_inventory(part_id)
```

For `Brake ECU Type-B`, deterministic fixture returns:

```text
source_location = Rack A19
available_quantity >= 1
```

### Robot Skill Fake

Expose a typed high-level skill contract for:

```text
transfer_part(
  part_id,
  quantity,
  source_location,
  destination
)
```

The fake represents the future robot skill boundary. It does not implement Nav2, MoveIt, VLA, or ros2_control.

### Action-status query

Expose:

```text
get_action_status(action_id)
```

This is required for reconciliation in MVP-004.

## 3. Gateway rules

- Agent calls typed tools only through the gateway;
- gateway validates request schema;
- runtime—not the LLM—owns timeout/retry policy;
- fakes must be deterministic and fault-injectable;
- no external process/network requirement.

## 4. Tests

- inventory lookup returns Rack A19;
- unavailable SKU is typed failure;
- transfer success returns typed result;
- same fixtures produce same results;
- malformed request is rejected;
- action status is queryable;
- raw ROS/Nav2/MoveIt access is absent.

## 5. Evidence

Create:

`results/mvp/MVP-003.json`

## 6. Exit Criteria

- [ ] one factory-tool gateway exists;
- [ ] WMS fake supports canonical mission;
- [ ] Robot Skill fake supports canonical mission;
- [ ] action status can be reconciled;
- [ ] typed errors exist;
- [ ] deterministic tests pass.

## 7. Commit

`feat(mvp): add deterministic factory tool gateway and skill fakes`

Do not start MVP-004.
