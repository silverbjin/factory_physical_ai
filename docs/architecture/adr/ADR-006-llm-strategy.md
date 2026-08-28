# ADR-006: LLM Model and Provider Strategy

## Status

Accepted for architecture; provider credential/runtime validation deferred.

## Context

The Agent needs typed tools, observability, replacement flexibility, and safe test behavior. No provider credentials or local model/GPU capability are established.

## Decision

Use a provider-neutral `ModelProvider` adapter with a deterministic fake provider for all unit/regression tests. The initial real-provider path is an API-hosted model supporting typed function calls; OpenAI Responses API is the first adapter candidate. Credentials are environment-injected only. Capture model identifier, input/output token counts where supplied, latency, and request/trace IDs without logging secrets.

## Alternatives

- Bind the mission engine directly to one SDK/model.
- Local LLM inference on the current WSL host.
- Prompt-text action parsing.

## Rationale

Hosted inference avoids the unverified local GPU path and typed calls keep semantic output constrained at the boundary.

## Trade-offs

API latency/cost/availability become dependencies; fake-provider tests cannot establish real provider quality.

## MVP usage

Fake provider by default; real API opt-in only with explicit local credentials and budget. A real provider is not a Day-10 MVP dependency.

## Final usage

Hosted provider behind the same adapter, with configured model allowlist, timeouts, token/cost telemetry, and fallback/HITL policy.

## Validation evidence

No provider SDK or credentials were inspected. OpenAI documents custom function tools with strongly typed arguments and outputs: https://platform.openai.com/docs/api-reference/responses-streaming/response/web_search_call?lang=curl

## Review trigger

Run a credential-safe structured-tool smoke test and record safe model/version, latency, token/cost fields when supplied, and failure category before accepting a specific model default, a real-provider demo, or an Agent benchmark claim.
