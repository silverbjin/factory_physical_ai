# SIM-010 observability regression

- Task: `TASK-SIM-010`
- Canonical source authority: `2ec859845628992b02686a6d8bcdbcb77985a5a2`
- Result: `SIM_OBSERVABILITY_REGRESSION_READY`
- Scope: simulation-only regression evidence; no physical or production-performance claim.

## Authority and qualification

Historical accepted authority remains the semantic oracle. Q01 (`TASK-SIM-Q01-MIN` acceptance, compatibility Evidence task `TASK-SIM-Q01`) is a separately preserved qualification observation. The canonical Evidence records the immutable acceptance/Evidence tuple, exact eleven operation subjects, claim scopes, predecessor bindings, applicability, and duplicate-authority checks. It does not backfill Q01 values into historical rows.

## Results

- Deterministic replay: `PASS`; it uses validated historical deterministic authority only. All eleven Q01 rows are explicitly non-replay authority.
- Physics semantic regression: `PASS`; historical semantics are compared with qualified actual observations, including validated applicable Gazebo and MuJoCo observations. This is not a bitwise-identity or real-world-performance claim.
- Full repository regression: `PROVEN_PREEXISTING`. Candidate `2ec859845628992b02686a6d8bcdbcb77985a5a2` and baseline `6909c6cceb727598570f6e170ae8d1d293418c9a` used `/home/jinho/projects/factory_physical_ai/.venv-sim/bin/python` (MuJoCo `3.13.0`) in clean detached worktrees with detached project-module imports. Both exited 1 with the same complete four-node failure set and the same non-empty stable signature for every node.

The detailed machine-verifiable record is [SIM-010_observability_regression.json](../../results/simulation/SIM-010_observability_regression.json).

## Repeatability and finalization

A fresh G7 execution from the same immutable candidate and baseline used the same explicitly resolved interpreter and clean detached worktrees. Its historical/Q01 bindings, subject mapping, claim scopes, applicability decisions, replay and physics decisions, final task result, complete failed-node set, and stable failure signatures were semantically equivalent to G6. Fresh worktree paths and raw-output hashes were intentionally not required to match.
