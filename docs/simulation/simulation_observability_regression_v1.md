# SIM-010 observability regression

- Task: `TASK-SIM-010`
- Canonical source authority: `2179d965b64abac79c068a94363b9a67e9f4739b`
- Result: `SIM_OBSERVABILITY_REGRESSION_READY`
- Scope: simulation-only regression evidence; no physical or production-performance claim.

## Authority and qualification

Historical accepted authority remains the semantic oracle. Q01 (`TASK-SIM-Q01-MIN`
acceptance, compatibility Evidence task `TASK-SIM-Q01`) remains a separately
preserved qualification observation. The canonical Evidence records the immutable
acceptance/Evidence tuple, exact eleven operation subjects, separately namespaced
`historical_oracle` and `qualification_observation` authority, claim scopes,
predecessor bindings, applicability, and duplicate-authority checks. It does not
backfill Q01 values into historical rows.

The requirement-scoped classification is `53` total: `21`
`HISTORICAL_DIAGNOSTIC_ONLY_NON_GATING`, `32` `EXPLICITLY_QUALIFIED_BY_Q01`,
and `0` `STILL_BLOCKING`.

## Results

- Deterministic replay: `PASS`; it uses validated historical deterministic
  authority only. All eleven Q01 rows are explicitly non-replay authority.
- Physics semantic regression: `PASS`; historical semantics are compared with
  qualified actual observations, including validated applicable Gazebo and MuJoCo
  observations. This is not a bitwise-identity or real-world-performance claim.
- Full repository regression: `PASS_PROVEN_PREEXISTING`. Candidate
  `2179d965b64abac79c068a94363b9a67e9f4739b` used its own clean detached source
  and test tree and recorded `396` collected, `4 failed`, and `392 passed`.
  Baseline `6909c6cceb727598570f6e170ae8d1d293418c9a` used its own clean detached
  source and test tree and recorded `341` collected, `4 failed`, and `337 passed`.
  Both used `/home/jinho/projects/factory_physical_ai/.venv-sim/bin/python`
  (MuJoCo `3.13.0`) with equivalent qualified environments. The `55` additional
  candidate-only tests are `EXPECTED_TEST_SUITE_EVOLUTION`; total/pass count
  equality is not required. The complete failed-node set and every corresponding
  non-empty stable signature match exactly.

The detailed machine-verifiable record is
[SIM-010_observability_regression.json](../../results/simulation/SIM-010_observability_regression.json).

## Repeatability and finalization

A fresh S10-G7 execution from the same immutable candidate and baseline used the
same qualified interpreter and distinct clean detached source/test trees. Its
accepted-source and Q01 bindings, exact subject set, claim scopes, applicability,
requirement-scoped classification, replay decision, physics semantic regression,
full-regression node/signature equivalence, and final task-specific result were
semantically equivalent to S10-G6. Only `generated_at` and temporary-worktree
paths differed.
