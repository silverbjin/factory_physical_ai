# Day-10 MVP Architecture Scope Reference

> Status: Reconciled by TASK-P0-002R on 2026-08-28.

The authoritative and only acceptance-scenario definition is [plans/day10_mvp_scope_v1.md](../../plans/day10_mvp_scope_v1.md). This architecture reference must not add a mission, failure, recovery, or acceptance variant.

For Day-10, the architecture applies that canonical scope to one local process with deterministic in-process `mock` fixtures, SQLite, and machine-readable evidence. The Agent may propose semantic capabilities only; the deterministic runtime validates every side effect and handles the canonical timeout reconciliation. Physical robot/camera/VLA, real factory services, real Nav2/MoveIt integration, and real-provider calls are not Day-10 acceptance work.

Future integration boundaries remain unchanged: Nav2 owns local navigation execution/recovery, MoveIt and `ros2_control` own motion/controller authority, and the deterministic runtime owns business-level policy after typed terminal results. Those later boundaries do not create additional Day-10 scenarios.
