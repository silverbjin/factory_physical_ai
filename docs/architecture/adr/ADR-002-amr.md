# ADR-002: AMR Strategy

## Status

Accepted for MVP; final hardware selection deferred.

## Context

The business scenario needs navigation state and failure recovery, but Phase 0 found ROS 2 Jazzy without Nav2, TurtleBot, or an AMR device.

## Decision

Use a deterministic navigation-skill mock for Day-10 and Agent evaluation. Target a minimal native ROS 2 Nav2/simulator or available AMR adapter only after the Agent vertical slice is proven.

## Alternatives

- Build Nav2/Gazebo first.
- Require existing myAGV/TurtleBot hardware for MVP.
- Omit navigation from the mission.

## Rationale

The mock preserves navigation contracts and failure paths while protecting schedule for Agent/VLA evidence.

## Trade-offs

No physical navigation evidence in MVP; mock behavior must be explicitly labelled.

## MVP usage

Named destination request returns deterministic success, blocked, timeout, or unavailable results.

## Final usage

Adapter to a native ROS 2 navigation stack with health and arrival verification.

## Validation evidence

Environment verification found ROS 2 Jazzy and no Nav2/TurtleBot packages or robot device.

## Review trigger

Review when a robot or native headless simulator is ready and the navigation adapter has an explicit integration exit criterion.
