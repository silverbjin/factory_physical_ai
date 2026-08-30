# Next VLA Task after TASK-P0-004

## Decision

```text
NO_GO
→ do not start real VLA implementation
→ TASK-W1-001 is not authorized
```

The current environment lacks verified CUDA execution, LeRobot/SmolVLA runtime prerequisites, selected and safely validated manipulator/camera paths, feasible teleoperation evidence, and an approved training budget.

## Authorized work

Only blocker remediation and a repeat of the non-destructive readiness gate are authorized:

1. select and approve the intended CUDA host and budget;
2. create a pinned isolated LeRobot environment on that host;
3. rerun GPU/Torch allocation and required LeRobot/SmolVLA import/config checks;
4. inventory the manipulator and camera on the native robot PC without motion;
5. document workspace limits, operator-controlled start, manual abort/E-stop, state feedback, and gripper path;
6. regenerate `results/phase0/P0-004_vla_readiness.json` and review the decision.

This is remediation for the existing gate, not authorization to collect Dataset V1, fine-tune SmolVLA, implement a VLA Skill Server, integrate Agent/ROS, or actuate hardware.

## Re-entry condition

`TASK-W1-001` may start only after all blocking readiness checks are `PASS`, the machine-readable evidence sets `next_task_authorized` to `true`, and the gate decision is explicitly reviewed. The Agent/MVP lane remains independent.
