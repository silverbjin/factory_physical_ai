# ADR-002: AMR Strategy

## Status

Accepted for MVP; final hardware selection deferred.

## Context

The business scenario needs navigation state and failure recovery. P0-002 verified ROS 2 Jazzy with Nav2 components, `nav2_simple_commander`, and minimal TB3/TB4 simulation packages, but no AMR device, map, controller configuration, or native robot-PC validation.

## Decision

Use a deterministic navigation-skill mock for Day-10 and Agent evaluation. For later integration, reuse installed Nav2 through an adapter that accepts only allowlisted named destinations. Nav2 owns local execution/recovery/lifecycle; the mission executor owns business retry, reassignment, and HITL after a typed terminal result.

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

P0-002 package/executable inspection verified Nav2 components, `nav2_simple_commander`, and minimal TB3/TB4 simulation packages. It verified no robot device or configured navigation environment.

## Review trigger

Review when a robot or native headless simulator is ready and the navigation adapter has an explicit integration exit criterion.
