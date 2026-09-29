# Evidence finalization — TASK-SIM-010

- Result: COMPLETE
- Canonical source authority: `2ec859845628992b02686a6d8bcdbcb77985a5a2`
- Canonical Evidence: `results/simulation/SIM-010_observability_regression.json`
- Companion report: `docs/simulation/simulation_observability_regression_v1.md`
- Evidence commit: `0c010f761e344df7e15a127c495a78828dd4208e`
- Validation: S10-G6 PASS; S10-G7 PASS; focused `38 passed`
- Deviation: NONE
- Next: `RUN_INDEPENDENT_REVIEW_S10_G8`

## Gate record

- G6 recorded immutable candidate source hashes, accepted predecessor and Q01 binding, exact eleven Q01 operation subjects, separate historical-oracle and qualification-observation namespaces, claim scope/applicability checks, historical-only replay, Gazebo/MuJoCo semantic comparison, and the complete G5 proof.
- G5 used candidate `2ec859845628992b02686a6d8bcdbcb77985a5a2` and baseline `6909c6cceb727598570f6e170ae8d1d293418c9a` in clean detached worktrees with `/home/jinho/projects/factory_physical_ai/.venv-sim/bin/python` and MuJoCo `3.13.0`. Both had the same complete four-node failure set and non-empty stable signatures, so the classification was `PROVEN_PREEXISTING`.
- G7 repeated the candidate/baseline execution with fresh detached worktrees. Authority, semantic results, replay decision, physics decision, final result, failed-node set, and stable signatures were equivalent; fresh runtime paths and output hashes were intentionally not required to match.

Canonical Evidence was generated; no Acceptance was recorded and the orchestrator was not resumed.
