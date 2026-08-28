# ADR-008: Persistence and Database

## Status

Accepted for MVP; target accepted conditionally.

## Context

Mission state, idempotency, evaluation metadata, and trace references must survive a process restart. Docker daemon access is unavailable and no database library is installed.

## Decision

Use SQLite for the single-process MVP mission/action/checkpoint store. Migrate to PostgreSQL before multi-process deployment, concurrent mission execution, or soak evidence. Redis is not a source of truth and is deferred unless an explicit queue/cache requirement arises.

## Alternatives

- PostgreSQL from day one.
- In-memory state.
- Redis as the primary store.

## Rationale

SQLite gives durable local evidence without blocked Docker infrastructure; PostgreSQL is the target for concurrent service operation.

## Trade-offs

SQLite does not validate service topology/concurrency; migration must be exercised before production-like claims.

## MVP usage

Single local SQLite file, transactionally recording mission transitions and idempotency keys.

## Final usage

PostgreSQL for mission/action/checkpoint/evaluation metadata; migrations and backups documented.

## Validation evidence

Docker daemon access is denied. LangGraph documentation distinguishes SQLite for lightweight/small-project use and PostgreSQL for production workloads: https://langchain-ai.github.io/langgraph/reference/checkpoints/?h=langgraph+checkpoint+sqlite+import+saver

## Review trigger

Migrate before concurrent workers, external deployment, or 24-hour soak validation begins.
