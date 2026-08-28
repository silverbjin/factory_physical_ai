# ADR-004: VLA / LeRobot Stack

## Status

Proposed — local installation and CUDA feasibility are not yet validated.

## Context

The portfolio needs direct VLA fine-tuning and dataset iteration. Current host has Python 3.12.3 but no Torch/LeRobot and blocked GPU access.

## Decision

Propose LeRobot with the `smolvla` extra and `lerobot/smolvla_base` as the initial VLA candidate. Store versioned local dataset manifests and run metadata; fine-tune only on an approved CUDA host. Keep an ACT baseline as a contingency, not a parallel model program. Before Dataset V1, complete a time-boxed VLA readiness decision: `GO` requires documented GPU/VRAM/driver facts, Torch CUDA visibility, LeRobot import, selected manipulator/camera path, and approved cost; `NO-GO` blocks Dataset V1/training and is escalated rather than replaced by synthetic evidence.

## Alternatives

- ACT only.
- Larger VLA family (pi0/pi0.5 or xvla).
- Custom training stack.

## Rationale

Official documentation presents SmolVLA as a 450M model intended for LeRobot datasets and direct fine-tuning. This matches the target learning loop while retaining a supported data/teleop toolchain.

## Trade-offs

Training cost/VRAM and dependency resolution are unproven locally. SmolVLA selection is not evidence that local training will succeed.

## MVP usage

Only the VLA skill contract/mock; no model download, training, or inference claim.

## Final usage

Fine-tuned SmolVLA deployed behind a versioned VLA Skill contract with dataset/config/commit/evaluation linkage.

## Validation evidence

`torch` and `lerobot` are absent; NVML GPU access is blocked. Official docs: https://huggingface.co/docs/lerobot/v0.4.4/smolvla . The documentation recommends the `smolvla` extra and shows fine-tuning/rollout paths.

## Review trigger

Accept after the VLA readiness `GO` criteria, isolated install/import, selected dataset recorder, and a non-training policy/config smoke validation. Complete the decision within two focused working days of beginning the VLA readiness task; reconsider ACT only if the documented GPU budget cannot support SmolVLA.
