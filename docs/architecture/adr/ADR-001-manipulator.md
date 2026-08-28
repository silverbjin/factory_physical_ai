# ADR-001: Manipulator Strategy

## Status

Deferred — no physical manipulator, serial device, or camera was verified **inside the current WSL development environment**.

## Context

The VLA learning loop requires direct demonstrations, stable teleoperation, camera observations, bounded action representation, and a safe execution path.

## Decision

Use a LeRobot-supported leader/follower low-cost manipulator pair (SO-101/SO-100 class or a documented adapter) as the preferred VLA data and skill platform after hardware validation. Do not commit to a specific kit until it is physically enumerated and its safety/port/camera setup is recorded.

## Alternatives

- Existing laboratory arm with a LeRobot adapter.
- Simulation-only demonstrations.
- Custom ROS arm stack without LeRobot compatibility.

## Rationale

LeRobot documents leader/follower teleoperation and camera-backed rollout paths; a supported pair minimizes adapter work and accelerates direct dataset ownership.

## Trade-offs

Low-cost arms have limited payload, repeatability, and safety features. They demonstrate the learning loop, not automotive production manipulation.

## MVP usage

Mock VLA skill; no motion or device command.

## Final usage

Single constrained pick/place cell with mechanical limits, operator start/stop, documented workspace, and a ROS adapter only where required.

## Validation evidence

`results/phase0/environment_verification.json` records no serial/camera devices exposed to WSL; this is not evidence that hardware is unavailable on a native robot PC. Official LeRobot SmolVLA rollout documentation describes supported leader/follower and OpenCV-camera fields: https://huggingface.co/docs/lerobot/v0.4.4/smolvla

## Review trigger

Accept only after device identity, leader/follower teleop, camera capture, calibration, stop path, and 10 short supervised episodes are evidenced.
