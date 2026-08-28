# Post-P0-002 Final Consistency Verification Prompt

Use this before MVP-001 if the modified architecture/ADR/contract files have not been independently reviewed.

```text
Perform a final read-only consistency review after TASK-P0-002.

Read:
- AGENTS.md
- context/*
- docs/architecture/system_architecture_v1.md
- docs/architecture/adr/*
- docs/contracts/contract_plan.md
- docs/environment/development_environment_v1.md
- docs/reviews/P0-001_architecture_review.md
- docs/reviews/P0-002_architecture_freeze_review.md
- plans/phase0_risks.md
- plans/next_tasks_after_phase0.md
- results/phase0/P0-002_architecture_freeze.json

Do not modify files.

Verify all of the following:
1. P0-003 VLA readiness does not block MVP-001.
2. Day-10 uses fixture-first in-process deterministic fakes.
3. Nav2 owns local navigation execution/recovery; runtime owns business recovery.
4. MoveIt/ros2_control retain motion/hardware authority; VLA cannot bypass them.
5. Agent cannot issue raw ROS/Nav2/joint commands.
6. physical action timeout has UNKNOWN -> RECONCILING semantics.
7. LLM cannot decide ambiguous physical outcome.
8. SQLite/JSONL/native processes are sufficient for Day-10.
9. physical robot/camera/VLA/real WMS/MES/PHM are out of Day-10 scope.
10. the only Day-10 business mission is parts transfer.
11. the only Day-10 failure is ambiguous Robot Skill timeout.
12. the only recovery path demonstrated is deterministic reconciliation + one bounded retry.
13. machine-readable evidence is mandatory.
14. no ADR contradicts the contract or system architecture.

Return:
- PASS/FAIL for each item
- exact file/section for any contradiction
- final decision: MVP-001 AUTHORIZED / NOT AUTHORIZED

Do not implement MVP-001.
```
