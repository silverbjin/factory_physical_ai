# ADR-003: Simulation Environment

## Status

Accepted for MVP; deferred for physical simulation.

## Context

The host lacks Gazebo/Isaac/Nav2 packages and GPU capability is unverified. Failure coverage matters more than visual fidelity.

## Decision

Use deterministic, fixture-driven skill/factory simulators for the Day-10 MVP and Chaos scenarios. Defer headless Gazebo/ROS 2 simulation selection until a native PC, package compatibility, and a concrete adapter test justify it.

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

ROS package inspection found no Nav2 or Gazebo package. GPU/NVML access is blocked.

## Review trigger

Adopt a physics simulator only when it validates an accepted interface or failure mode not covered by fixtures.
