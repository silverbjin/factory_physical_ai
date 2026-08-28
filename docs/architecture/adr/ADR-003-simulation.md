# ADR-003: Simulation Environment

## Status

Accepted for MVP; deferred for physical simulation.

## Context

The host has Gazebo `gz sim` and Nav2 components, but lacks a configured world/map, robot/controller configuration, and validated native hardware topology. GPU capability remains unverified. Failure coverage matters more than visual fidelity.

## Decision

Use deterministic, fixture-driven skill/factory simulators for the Day-10 MVP and Chaos scenarios. Defer use of the installed Gazebo/ROS 2 simulation capability until a concrete adapter test justifies it; do not spend the MVP window creating maps or visual polish.

## Alternatives

- Install/tune Gazebo and Nav2 now.
- Isaac Sim/Lab.
- Photorealistic digital twin.

## Rationale

Fixtures enable repeatable failure, idempotency, and recovery tests immediately and avoid unverified GPU/GUI overhead.

## Trade-offs

Kinematic/physics fidelity is absent until a later scoped integration task.

## MVP usage

Deterministic simulated adapters only, explicitly tagged `mock` in traces.

## Final usage

Headless Gazebo/ROS 2 integration is preferred if it exercises a real adapter; physical hardware provides the VLA evidence.

## Validation evidence

P0-002 inspection verified `gz sim`, Nav2 components, and minimal Nav2 simulation packages. GPU/NVML access remains blocked; no simulator world or robot configuration has been validated.

## Review trigger

Adopt a physics simulator only when it validates an accepted interface or failure mode not covered by fixtures.
