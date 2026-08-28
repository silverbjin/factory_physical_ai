# ADR-007: Agent Orchestration Framework

## Status

Accepted for MVP.

## Context

The project needs durable missions, recovery, HITL, testability, and bounded physical execution. LangGraph offers persistence/checkpointers and interrupts, but no framework is installed and framework state cannot be the sole physical-operation authority.

## Decision

Implement a small custom deterministic mission state machine with an LLM/provider boundary: a finite transition table, SQLite checkpoint/action records, and one explicit HITL state. Persist state and side-effect action records independently. Treat LangGraph as an optional later orchestration adapter/spike, never as a replacement for executor safety, idempotency, or reconciliation.

## Alternatives

- LangGraph as the primary mission engine.
- Ad hoc ReAct loop.
- Multi-agent framework.

## Rationale

The custom core directly maps mission transitions, retry budgets, and physical idempotency to tested deterministic code within the six-week scope.

## Trade-offs

Some graph/HITL plumbing is implemented locally; a future LangGraph adoption needs adapter work.

## MVP usage

Single orchestrator, fake model, SQLite checkpoint/action log, explicit HITL state.

## Final usage

Same core with PostgreSQL and optional LangGraph integration only if it offers a measured benefit without weakening contracts.

## Validation evidence

LangGraph is not installed. Its official docs describe SQLite/Postgres checkpointers and durable interrupts: https://langchain-ai.github.io/langgraph/reference/checkpoints/?h=langgraph+checkpoint+sqlite+import+saver and https://langchain-ai.github.io/langgraph/how-tos/human_in_the_loop/breakpoints/

## Review trigger

Revisit after custom restart/HITL tests exist; adopt LangGraph only with a compatibility spike and unchanged deterministic executor contract.
