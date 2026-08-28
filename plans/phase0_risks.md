# Phase 0 Risk Register

> Updated by TASK-P0-002 on 2026-08-28. Scores are planning assessments, not measured results.

| ID | Risk / disposition | Evidence | Owner and required action | Trigger / exit signal |
|---|---|---|---|---|
| R-01 | **CRITICAL — VLA readiness can block direct-learning evidence** | GPU/NVML blocked; Torch/LeRobot absent; no camera or serial device exposed to WSL | Lead Engineer: complete a VLA readiness `GO`/`NO-GO` within two focused working days of beginning the readiness task. `GO` requires CUDA facts, Torch CUDA, LeRobot import, hardware/camera path, and training budget. `NO-GO` escalates and blocks Dataset V1 rather than fabricating evidence. | Before Dataset V1 planning or collection. Does not block MVP-001. |
| R-02 | **HIGH — WSL absence can be misread as hardware absence** | Device enumeration observes only WSL; native robot PC is uninspected | Inventory the actual native robot-PC/device path without motion; retain WSL as development-only. | Before scheduling hardware/teleop work. |
| R-03 | **HIGH — ROS/VLA control coupling can bypass standard safety ownership** | Nav2, MoveIt, `ros2_control` are installed; contracts previously lacked explicit ownership/reconciliation | Preserve P0-002 ownership rules and add contract tests before ROS/VLA adapter work. | Before INT-001 or physical skill work. |
| R-04 | **HIGH — Day-10 scope can expand into services/simulation** | Original task order put hardware gates before Agent MVP; many boundaries are mockable | Keep frozen one-process fixture scope. Tooling and MVP-001 proceed before/alongside VLA readiness. | MVP-001 design review. |
| R-05 | **MEDIUM — Real provider behavior is unmeasured** | No credentials, SDK, latency/cost, or structured-call smoke evidence | Use fake provider for MVP; perform a credential-safe real-provider smoke check only before real demo/benchmark claim. | Before real-provider demo or Agent benchmark. |
| R-06 | **MEDIUM — Camera defaults are hypotheses** | No camera exposed; 640x480@30 is not measured | Validate capture rate, timestamp/action alignment, calibration revision, and storage bandwidth in smoke recording. | Before Dataset V1. |
| R-07 | **MEDIUM — Docker/telemetry can block early evidence unnecessarily** | Docker daemon unavailable; collector not configured | Keep SQLite/JSONL for single-process regression/Chaos/soak; require PostgreSQL/collector only for concurrent or multi-service claims. | Before concurrent/multi-service deployment. |
| R-08 | **MEDIUM — custom orchestration can grow into framework reimplementation** | Custom state machine selected; LangGraph optional | Limit MVP to finite transitions, SQLite records, one HITL state; no LangGraph spike without measured gap. | Restart/idempotency test exposes a gap. |
| R-09 | **LOW — installed Nav2/Gazebo may tempt premature simulator work** | Nav2/Gazebo capability exists but no configured environment | Use fixtures first; use installed stack only to validate a concrete later adapter boundary. | INT-001 has a specific integration criterion. |

## Critical-path rule

MVP-001 is independent of R-01/R-02. VLA readiness is parallel and time-boxed; it is a hard prerequisite only for teleoperation, Dataset V1, training, and physical VLA claims.
