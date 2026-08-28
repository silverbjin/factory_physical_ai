# TASK-P0-002R — Architecture Freeze Reconciliation

> Status: READY FOR EXECUTION
> Phase: Phase 0 corrective review
> Depends on: TASK-P0-002
> Gate: Final Architecture Freeze
> Scope: documentation / ADR / freeze evidence only
> Application implementation: FORBIDDEN
> MVP-001 authorization before completion: NO

## 1. Goal

Resolve the contradictions found by the post-P0-002 read-only verification so that the repository has exactly one authoritative Day-10 scope and a valid Architecture Freeze evidence trail.

The frozen Day-10 invariant is:

> **1 Mission + 1 Failure + 1 Recovery + Evidence**

Canonical mission:

> `Line B에 Brake ECU Type-B 1개를 공급해줘.`

Canonical failure:

> First Robot Skill execution returns an ambiguous timeout.

Canonical recovery:

> `TIMEOUT -> UNKNOWN -> RECONCILING -> typed action-status query -> FAILED/retryable -> exactly one retry -> SUCCEEDED -> COMPLETED`

Do not add or preserve alternative Day-10 failures or recovery variants.

---

## 2. Required inputs

Read:

- `AGENTS.md`
- `context/*.md`
- `plans/day10_mvp_scope_v1.md`
- `docs/architecture/day10_mvp_scope_v1.md`
- `docs/architecture/system_architecture_v1.md`
- `docs/contracts/contract_plan.md`
- `docs/architecture/adr/ADR-002-amr.md`
- all other ADRs under `docs/architecture/adr/`
- `docs/reviews/P0-001_architecture_review.md`
- any existing P0-002 review/freeze artifacts
- `plans/next_tasks_after_phase0.md`
- `tasks/TASK-MVP-001.md`
- `results/phase0/environment_verification.json`

Before modifying files, inspect `git status`.

---

## 3. Blocking findings to resolve

### B-01 — Duplicate Day-10 scope documents disagree

Current problem:

- `plans/day10_mvp_scope_v1.md` freezes one failure and one recovery.
- `docs/architecture/day10_mvp_scope_v1.md` permits multiple alternative failures/recoveries.

Required resolution:

1. Make `plans/day10_mvp_scope_v1.md` the **canonical source of truth** for Day-10 scope.
2. `docs/architecture/day10_mvp_scope_v1.md` must not contain an independent divergent scope.
3. Prefer one of:
   - replace the architecture document with a short pointer/reference to the canonical plan; or
   - make its scope wording exactly consistent with the canonical plan.
4. There must be no Day-10 alternative failure list.

The only Day-10 failure is:

```text
Robot Skill attempt #1
  -> TIMEOUT
  -> UNKNOWN
```

The only Day-10 recovery is:

```text
UNKNOWN
  -> RECONCILING
  -> get_action_status(action_id)
  -> FAILED + retryable=true
  -> one bounded retry
  -> SUCCEEDED
  -> COMPLETED
```

---

### B-02 — ADR-002 expands Day-10 with navigation outcomes

Current problem:

`ADR-002-amr.md` allows additional navigation outcomes/recovery behavior in MVP usage.

Required resolution:

- Keep Nav2 ownership and future AMR integration policy.
- Move navigation failure/recovery variants to **post-Day-10 integration scope**.
- For Day-10, navigation is represented only by the deterministic Robot Skill Fake boundary.
- ADR-002 must explicitly state:

```text
Day-10 MVP:
No real Nav2 execution is required.
No navigation failure scenario is part of the Day-10 acceptance test.
Navigation variants belong to later ROS/AMR integration tasks.
```

Do not weaken the existing rule:

- Nav2 owns local navigation execution/recovery.
- Deterministic Runtime owns business-level recovery after typed terminal results.

---

### B-03 — Missing P0-002 freeze review artifact

Create exactly:

`docs/reviews/P0-002_architecture_freeze_review.md`

It must record:

- verification date;
- reviewed artifacts;
- B-01/B-02 resolution;
- F-01~F-16 final disposition;
- deferred gates;
- accepted constraints;
- final scope invariant;
- final decision.

The final decision may be `GO` only if every Exit Criterion in this task passes.

---

### B-04 — Missing P0-002 freeze evidence JSON

Create exactly:

`results/phase0/P0-002_architecture_freeze.json`

Required minimum structure:

```json
{
  "task": "TASK-P0-002",
  "verification_task": "TASK-P0-002R",
  "status": "GO",
  "architecture_version": "v1.0",
  "mvp_scope": "day10",
  "scope_invariant": "1 Mission + 1 Failure + 1 Recovery + Evidence",
  "canonical_failure": "ambiguous_robot_skill_timeout",
  "canonical_recovery": "reconcile_then_one_bounded_retry",
  "critical_findings_resolved": ["F-01", "F-02", "F-03"],
  "high_findings_resolved_for_architecture": ["F-04", "F-05", "F-06", "F-07", "F-10"],
  "deferred_findings": ["F-08", "F-09", "F-11", "F-12", "F-15"],
  "accepted_constraints": ["F-13", "F-14", "F-16"],
  "physical_robot_authorized": false,
  "vla_runtime_authorized": false,
  "mvp_001_authorized": true
}
```

Populate only verified facts.

If any contradiction remains:

- set `status` to `CONDITIONAL_GO`;
- set `mvp_001_authorized` to `false`;
- list remaining blockers.

---

### B-05 — Task-ID naming consistency for VLA readiness

The read-only verification found that the repository currently calls the VLA readiness task `P0-004`, while earlier planning material may refer to `P0-003`.

Required resolution:

1. Inspect the actual task files and `plans/next_tasks_after_phase0.md`.
2. Do **not** renumber an existing task merely to match an old example.
3. If the actual VLA readiness task is `P0-004`, use `P0-004` consistently in all current planning/freeze documents.
4. If `P0-003` exists for a different purpose, preserve it.
5. Record the final ID in the freeze review.

The invariant is dependency, not the number:

```text
Architecture Freeze
  ├── Day-10 MVP path
  └── VLA Readiness path (parallel; must not block MVP-001)
```

---

## 4. Canonical Day-10 scope

### Mission

```text
Line B에 Brake ECU Type-B 1개를 공급해줘.
```

Fixture:

```text
part_id         Brake ECU Type-B
quantity        1
source_location Rack A19
destination     Line B
```

### Normal path

```text
Operator
 -> Factory Agent
 -> Structured Mission
 -> Deterministic Runtime
 -> WMS Fake
 -> Robot Skill Fake
 -> COMPLETED
 -> SQLite / machine-readable evidence
```

### Single failure path

```text
Robot Skill attempt #1
 -> TIMEOUT
 -> action UNKNOWN
 -> mission RECONCILING
 -> get_action_status(action_id)
 -> FAILED / retryable=true
 -> RECOVERING
 -> exactly one retry
 -> SUCCEEDED
 -> COMPLETED
```

### Explicitly not Day-10 acceptance scenarios

- inventory mismatch;
- blocked navigation path;
- robot unavailable;
- PHM warning;
- VLA grasp failure;
- camera failure;
- real provider outage;
- ROS node restart;
- DB disconnect;
- network latency;
- any second failure.

These belong to later Agent/Integration/Chaos work.

---

## 5. Allowed changes

May modify:

- `plans/day10_mvp_scope_v1.md` only if needed for wording consistency;
- `docs/architecture/day10_mvp_scope_v1.md`;
- `docs/architecture/adr/ADR-002-amr.md`;
- another ADR only if an exact Day-10 contradiction is found;
- `plans/next_tasks_after_phase0.md` only for task-ID consistency;
- `docs/reviews/P0-002_architecture_freeze_review.md`;
- `results/phase0/P0-002_architecture_freeze.json`.

May create:

- `docs/reviews/P0-002_architecture_freeze_review.md`;
- `results/phase0/P0-002_architecture_freeze.json`.

Must NOT modify:

- `src/**`;
- tests implementing MVP behavior;
- `TASK-MVP-001.md` unless a purely documentary prerequisite reference is factually wrong;
- physical robot configuration;
- VLA code/model/data;
- ROS integration code;
- credentials;
- unrelated files.

---

## 6. Required read-only verification after edits

After changes, perform a fresh consistency check.

All must PASS:

1. VLA readiness path does not block MVP-001.
2. fixture-first in-process deterministic fakes are Day-10 implementation.
3. Nav2 local ownership vs Runtime business ownership remains explicit.
4. MoveIt/ros2_control authority remains explicit.
5. Agent cannot issue raw ROS/Nav2/joint commands.
6. timeout uses `UNKNOWN -> RECONCILING`.
7. LLM cannot decide ambiguous physical outcome.
8. SQLite/JSONL/native process is sufficient for Day-10.
9. physical robot/camera/VLA/real factory systems are out of Day-10.
10. only one business mission is in Day-10.
11. only one failure is in Day-10: ambiguous Robot Skill timeout.
12. only one demonstrated recovery is in Day-10: reconciliation + exactly one bounded retry.
13. machine-readable evidence is mandatory.
14. no ADR contradicts the canonical scope or contract.
15. P0-002 freeze review exists at the exact required path.
16. P0-002 freeze JSON exists at the exact required path and records the correct status.

---

## 7. Validation commands

Run at minimum:

```bash
git status
git diff --check
```

Also search for conflicting Day-10 scope language, including terms such as:

```text
inventory mismatch
navigation failure
blocked path
robot unavailable
PHM
VLA grasp
alternative failure
retry / wait / reassign / HITL
```

A term may appear in future-scope documentation, but it must not be described as an allowed Day-10 acceptance scenario.

---

## 8. Exit Criteria

- [ ] canonical Day-10 scope has one authoritative source;
- [ ] duplicate architecture scope no longer broadens it;
- [ ] ADR-002 no longer adds Day-10 navigation failure/recovery variants;
- [ ] VLA readiness task ID is consistent with actual repository tasks;
- [ ] `docs/reviews/P0-002_architecture_freeze_review.md` exists;
- [ ] `results/phase0/P0-002_architecture_freeze.json` exists;
- [ ] freeze JSON status is `GO`;
- [ ] `mvp_001_authorized` is `true`;
- [ ] all 16 post-fix checks PASS;
- [ ] `git diff --check` passes;
- [ ] no application source code changed.

Only after all checks pass may the final report state:

> `MVP-001 implementation is authorized.`

Otherwise state:

> `MVP-001 implementation is NOT authorized.`

Do not start MVP-001 in this task.

---

## 9. Recommended commit

After all Exit Criteria pass:

```text
docs(arch): reconcile day-10 scope and finalize architecture freeze
```

Do not combine MVP implementation with this commit.
