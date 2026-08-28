# Day-10 MVP Scope v1

> Status: Frozen by TASK-P0-002 on 2026-08-28. This scope authorizes no implementation by itself.

## Objective

Demonstrate one simulated, production-oriented line-side logistics mission: a validated natural-language goal is processed through deterministic mission control, produces typed mock tool/skill calls, recovers from one injected failure, persists its state/action record, and emits machine-readable evidence.

## In scope

- One local process: deterministic mission executor, finite state-transition table, one HITL state, and SQLite checkpoint/action store.
- One fake model provider; no provider credential, network call, or real-model claim.
- One in-process factory-tool gateway containing typed, deterministic `mock` fixtures for WMS/Fleet/PHM, named navigation, VLA skill, and verification.
- Canonical mission: `Supply Brake ECU Type-B to Line B.`
- One representative injected recovery path selected from inventory mismatch, robot unavailable/PHM restriction, navigation unavailable, or VLA failure.
- JSONL trace/run metadata containing the MVP contract profile, including IDs, outcome, error/retryability, and mock source declaration.

## Explicitly out of scope

- LeRobot install, model download, teleoperation, Dataset V1, training, camera capture, or physical manipulation.
- ROS 2 nodes, Nav2 maps/worlds, Gazebo world configuration, MoveIt configuration, `ros2_control` hardware/controller setup, or robot motion.
- Docker Compose, PostgreSQL, OpenTelemetry collector, Grafana, real LLM provider calls, multi-agent orchestration, or UI.

## Boundary rules

The Agent proposes an allowlisted semantic capability. The deterministic executor validates and records every side effect. Fixtures return typed observations only. Later Nav2 owns local navigation recovery; MoveIt and `ros2_control` own staging/collision/trajectory/controller behavior; the Agent and VLA cannot bypass those boundaries.

## Exit evidence for the later MVP-001 task

The implementation task must produce automated tests plus a run manifest/trace showing one mission ID, durable state transitions, one bounded recovery, no duplicate action after reconciliation, and final typed verification. Mock results must never be presented as hardware, VLA, or provider measurements.
