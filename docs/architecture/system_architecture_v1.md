# System Architecture v1

> Status: Accepted for the Phase 0 MVP boundary. Hardware-specific adapters remain proposed until their validation gates pass.

## Context

```text
 Operator
    | natural-language line-side supply goal
    v
 Factory AI Agent (semantic reasoning only)
    | typed tool proposals / recovery choice
    v
 Deterministic Mission Executor -----------------------------------------------+
    | schema, authorization, timeout, retry, idempotency, persistence, audit   |
    +---- Factory tool adapters: WMS / Fleet / PHM (mock in Day-10)             |
    +---- Navigation-skill adapter ----------> ROS 2 AMR adapter (mock in MVP)  |
    +---- VLA-skill adapter -----------------> VLA server -> manipulator        |
    +---- Verification adapter -------------> vision / rule result              |
    |                                                                         |
    +---- traces, metrics, run manifests ------------------------------------> Evidence store
```

This is a project interpretation of SDF-style manufacturing integration, not a claim about any proprietary Hyundai AutoEver architecture.

## Phase 0 decision register

| ID | Area | Status | Frozen direction and rationale |
|---|---|---|---|
| D1 | Manipulator | Deferred | LeRobot-supported leader/follower preferred, but no physical device was verified (ADR-001). |
| D2 | AMR | Accepted for MVP | Deterministic navigation mock first; native ROS 2 AMR/Nav2 path later (ADR-002). |
| D3 | Simulation | Accepted for MVP | Fixture-driven simulator first; physical simulation deferred until it proves an integration boundary (ADR-003). |
| D4 | VLA / LeRobot | Proposed | LeRobot + SmolVLA candidate; local install/CUDA gate is still open (ADR-004). |
| D5 | Camera | Proposed | One fixed RGB 640x480@30 FPS source, with timestamp/calibration metadata (ADR-005). |
| D6 | LLM strategy | Accepted for architecture | Hosted API behind a provider-neutral typed-tool adapter; tests use a fake provider (ADR-006). |
| D7 | Orchestration | Accepted for MVP | Custom deterministic mission executor; LangGraph is optional and cannot own safety/idempotency (ADR-007). |
| D8 | Persistence | Accepted for MVP | SQLite now, PostgreSQL before concurrent/soak deployment (ADR-008). |
| D9 | Observability | Accepted for MVP | Structured JSONL/run manifests now; OpenTelemetry stack after service topology is proven (ADR-009). |
| D10 | Deployment | Accepted for MVP | Native local processes now; containerize service plane later, keep hardware edge native (ADR-010). |
| D11 | ROS 2 architecture | Accepted for planning | Namespaced, typed execution adapters; no Agent ROS-shell/raw-motion path. |
| D12 | Development/robot split | Accepted for planning | WSL PC is service/dev only; robot PC and CUDA host are separate, validated roles. |
| D13 | Repository/tooling | Accepted for planning | Pinned project venv with `uv`, pytest, Ruff, mypy, pre-commit and result manifests is next task; no system-wide package mutation in Phase 0. |

## Responsibility boundaries

| Component | Owns | Must not own |
|---|---|---|
| Factory AI Agent | goal interpretation, semantic decomposition, approved tool selection, recovery proposal | raw motor commands, unrestricted ROS commands, success assertions without a verification result |
| Deterministic Mission Executor | contract validation, state transitions, permission/safety gates, timeout/retry budget, idempotency, persistence, metrics | free-form semantic decision making |
| Factory adapters | WMS, Fleet, and PHM request/response translation | inventing factory state or bypassing executor policy |
| Navigation skill | controlled navigation intent and structured execution result | agent-driven shell or trajectory commands |
| VLA skill | validated observation-to-action policy invocation and structured outcome | mission authorization, retry policy, or unbounded policy rollout |
| ROS 2 adapters | native driver lifecycle, sensor state, execution, diagnostics | Agent reasoning or persistence ownership |
| Verification | observed part/placement evidence and confidence | declaring mission completion by itself |

## Runtime placement

```text
Phase 0 / Day-10: WSL development PC
  Agent + deterministic executor + mock WMS/Fleet/PHM + SQLite + JSONL traces
  Deterministic fake navigation/VLA/verification adapters

Final integration: service/development PC                    robot-edge PC
  Agent / executor / DB / telemetry                   ROS 2 drivers / cameras / skills
  provider API egress                                 AMR + manipulator hardware
```

The verified host is WSL2 and has no robot device evidence; actual robot execution therefore belongs to a native Linux robot PC. Training occurs only on a CUDA-ready approved host. Services and edge nodes communicate over allowlisted versioned APIs; ROS discovery remains on a dedicated, explicitly configured domain.

## Control and data flow

1. An operator submits a validated mission with `mission_id` and `idempotency_key`.
2. The executor snapshots structured WMS, Fleet, and PHM state through adapters.
3. The Agent may propose only an approved, typed tool/skill call.
4. The executor validates schema, authorization, current state, and bounded policy budgets before dispatch.
5. The adapter returns a typed observation/result, including retryability and a correlation ID.
6. Verification is required before physical-action success is committed.
7. On a failure, deterministic policy either retries within budget, asks the Agent for an approved recovery, or creates a HITL request.
8. Every transition and external call is correlated by `mission_id`, recorded durably, and exported as evaluation evidence.

## MVP mocks and final integration

| Boundary | Day-10 MVP | Final integration intent |
|---|---|---|
| WMS / Fleet / PHM | deterministic fixtures with injected failures | versioned adapters to services or controlled emulators |
| AMR navigation | deterministic navigation-skill mock | ROS 2 adapter, with Nav2/simulator only when a native validation environment is ready |
| VLA manipulation | structured skill mock | LeRobot/SmolVLA-controlled skill service on a validated hardware path |
| vision verification | deterministic fixture | camera-backed verifier with calibrated observation contract |
| persistence | SQLite file, local | PostgreSQL after multi-process/soak requirements are active |
| traces/metrics | JSONL structured logs and local Prometheus-compatible metrics | OpenTelemetry collector + Prometheus/Grafana or equivalent |

## ROS 2 plan

Names are a contract plan, not currently running nodes:

```text
/factory/<cell_id>/amr/navigation_adapter
/factory/<cell_id>/manipulator/execution_adapter
/factory/<cell_id>/perception/verification_adapter
/factory/<cell_id>/health/diagnostics_adapter
/factory/<cell_id>/mission/ros_execution_bridge
```

The bridge accepts only validated skill requests from the executor and returns structured results. It does not expose a ROS CLI or raw topic publishing interface to the Agent. Lifecycle/health diagnostics and `ROS_DOMAIN_ID` configuration are validation requirements of the ROS integration task.
