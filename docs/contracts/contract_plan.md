# Contract Boundary Plan v1

> Status: planning contract for subsequent implementation. Schema version `v1` is planned; this document does not define executable APIs yet.

## Cross-cutting envelope

Every request, event, and result crossing a component boundary must include the following unless explicitly marked inapplicable:

| Field | Requirement |
|---|---|
| `schema_version` | Required, semver-compatible contract version. |
| `mission_id` | Required stable UUID for the business mission. |
| `request_id` | Required unique UUID per attempted call. |
| `idempotency_key` | Required for every side-effecting operation; stable across safe retries. |
| `correlation_id` / `trace_id` | Required for observability; may equal `mission_id` initially. |
| `timestamp` | Required ISO 8601 UTC emission time. |
| `deadline_at` and `timeout_ms` | Required execution deadline and local timeout semantics. |
| `result` | Required `success`, `failure`, `pending`, or `requires_human`. |
| `error` | Required on non-success: code, message, category, retryable, and safe detail. |
| `attempt` / `retry_budget_remaining` | Required for retryable external actions. |
| `component_version` | Required on result-producing services. |
| `evidence_refs` | Optional immutable references to trace, image, or run artifact; no secret data. |

The executor validates all envelopes before dispatching. An Agent proposal that fails validation never reaches a robot adapter.

## Planned contracts

| Contract | Request / state essentials | Result essentials | Safety and failure policy |
|---|---|---|---|
| **Mission** | `mission_id`, goal, priority, line, requested part/quantity, state, idempotency key, approval context | transition, checkpoint revision, outcome, HITL request | only deterministic transition table may mutate state; recovery and cancellation are auditable |
| **Factory Tool** | tool name/version, typed arguments, allowed operation, timeout/deadline | structured payload or typed error, source timestamp, freshness | tools return observations; tool-side effects require idempotency and authorization |
| **Robot/Fleet State** | robot ID, capability, location, availability, mission assignment, source timestamp | eligibility decision/reason, health reference | stale state is a failure; Agent cannot fabricate eligibility |
| **PHM State** | robot/equipment ID, health state, severity, evidence timestamp, restrictions | `eligible`, `restricted`, or `unavailable` with policy reason | executor excludes restricted equipment according to deterministic policy |
| **Navigation Skill** | robot ID, approved named destination/route, speed profile ID, action ID, timeout | execution state, arrival verification, diagnostic error, retryability | no raw poses/trajectories from the Agent; adapter enforces maps and limits |
| **VLA Skill** | robot ID, task ID, policy/model version, observation refs, approved workspace profile, timeout | pick/place outcome, verifier input refs, policy latency, failure taxonomy | no direct actuator contract; policy is bounded by adapter, workspace, and stop policy |
| **Verification Result** | verifier ID/version, expected part/place, observation refs, timestamp | pass/fail/uncertain, confidence, mismatch taxonomy | mission completion needs deterministic acceptance threshold; uncertainty escalates or recovers |

## Error taxonomy and timeout rules

Use machine-readable categories: `VALIDATION`, `AUTHORIZATION`, `SAFETY_POLICY`, `DEPENDENCY_TIMEOUT`, `DEPENDENCY_MALFORMED`, `RESOURCE_UNAVAILABLE`, `EXECUTION_FAILED`, `VERIFICATION_MISMATCH`, `MODEL_TIMEOUT`, `MODEL_FAILURE`, `CANCELLED`, and `INTERNAL`.

- Each tool declares a finite timeout and retry budget; callers may never infer unlimited retries.
- `retryable` is supplied by the adapter but policy decides whether a retry is allowed.
- Timeouts do not imply a physical action failed or succeeded. The executor must reconcile the action ID before retrying or resuming.
- Contract changes require a version bump, compatibility note, and contract-test update before implementation.
