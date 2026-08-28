# ADR-010: Deployment and Service Topology

## Status

Accepted for MVP; containerized target deferred behind Docker and hardware gates.

## Context

The verified WSL host has Docker CLI but cannot access the daemon. Hardware drivers/cameras are absent and should not be containerized merely for symmetry.

## Decision

Run the MVP as local processes on the development PC: Agent/executor, factory mocks, SQLite, and JSONL evidence. For target integration, containerize stateless IT-side services (Agent API, factory emulators, PostgreSQL, telemetry) while running ROS 2 drivers, camera acquisition, VLA inference, and robot control natively on the robot/edge PC.

## Alternatives

- Containerize every component, including hardware drivers.
- Require Docker Compose for the MVP.
- Run all control services on the robot PC.

## Rationale

This keeps hardware access and safety lifecycle local while retaining reproducible service boundaries where containers add value.

## Trade-offs

Two deployment modes require clear config/version management; container reproducibility is not yet verified.

## MVP usage

Native local process topology, mock-only external boundaries, no Docker claim.

## Final usage

Containerized service plane plus native robot edge plane, explicit network allowlists and ROS domain separation.

## Validation evidence

Docker 29.6.1 CLI is present, but `docker info` fails with access denied to `/var/run/docker.sock`; no image was pulled.

## Review trigger

Introduce Compose only after scoped daemon access and an explicitly authorized smoke image/service test succeed; review hardware containerization only with a device-specific reason.
