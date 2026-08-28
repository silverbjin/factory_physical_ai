# ADR-009: Observability

## Status

Accepted for MVP; extended stack deferred.

## Context

The project requires correlatable mission/tool/skill evidence, latency, failure categories, and later Chaos/Soak evidence. Only `prometheus_client` is present locally; no collector is configured.

## Decision

MVP emits structured JSONL events and a machine-readable run manifest with `mission_id`, `request_id`, timestamps, state transition, model/tool/skill version, latency, failure category, retry/HITL decision, and artifact references. Expose Prometheus-compatible metrics when the runtime is created. Add OpenTelemetry traces plus a collector and Prometheus/Grafana only when service topology is validated.

## Alternatives

- LangSmith-only telemetry.
- Logs only.
- Full ELK/Jaeger/Grafana stack in Phase 0.

## Rationale

Local structured evidence is sufficient to start deterministic evaluation without creating an unvalidated observability platform.

## Trade-offs

Cross-service visualization is deferred; JSONL schema discipline is required from the first MVP task.

## MVP usage

JSONL trace/run manifests and optional local metrics endpoint; no secrets or raw sensitive images by default.

## Final usage

OpenTelemetry traces correlated with metrics/logs and retained run artifacts for benchmark/Chaos/Soak reports.

## Validation evidence

`prometheus_client` imports in the current Python interpreter; OpenTelemetry is not installed. This is a local capability check, not telemetry performance evidence.

## Review trigger

Add collector/dashboard after at least two services emit the shared correlation fields or before Chaos/Soak reporting.
