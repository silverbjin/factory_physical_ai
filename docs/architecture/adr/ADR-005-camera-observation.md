# ADR-005: Camera and Observation Configuration

## Status

Proposed — no camera is currently enumerated.

## Context

VLA needs timestamped image and robot-state observations, while verification needs traceable evidence. Adding cameras prematurely increases calibration and synchronization risk.

## Decision

Use one fixed external RGB camera for V1 at 640x480, 30 FPS, with monotonic capture timestamps. LeRobot/OpenCV owns VLA recording; a versioned observation adapter provides selected frames/metadata to ROS verification when needed. Record extrinsic/intrinsic calibration and clock-source metadata; a wrist camera is out of V1.

## Alternatives

- Two cameras from the outset.
- ROS-only camera pipeline.
- Uncalibrated webcam input.

## Rationale

One view minimizes hardware and synchronization variables while matching the official example camera configuration.

## Trade-offs

Occlusion/generalization may limit performance; add a second view only after failure taxonomy proves its value.

## MVP usage

Synthetic observation references in fixtures.

## Final usage

Camera capture runs adjacent to the robot; dataset records image timestamps plus action/state alignment and calibration revision.

## Validation evidence

No `/dev/video*` device or `v4l2-ctl` was observed. LeRobot SmolVLA documentation illustrates a 640x480/30 FPS OpenCV camera configuration: https://huggingface.co/docs/lerobot/v0.4.4/smolvla

## Review trigger

Accept after capture enumeration, frame-rate/timestamp test, calibration manifest, and a short supervised recording.
