# Gate Finalization — TASK-SIM-010

- Result: PASS — S10-G6 CANONICAL_SIM010_EVIDENCE and S10-G7 REPEATABILITY_AND_FINALIZATION
- Event type: Review-style manual gate finalization; this is not S10-G8 Acceptance.
- Canonical Evidence: `results/simulation/SIM-010_observability_regression.json`
- Canonical report: `docs/simulation/simulation_observability_regression_v1.md`
- Canonical Evidence commit: `f7a135a0bc3d6f9b22fc17f63b838ed17bde0217`

## Immutable provenance

- Source candidate: `2179d965b64abac79c068a94363b9a67e9f4739b`
- Baseline: `6909c6cceb727598570f6e170ae8d1d293418c9a`
- Canonical Evidence `source_git_sha`: `2179d965b64abac79c068a94363b9a67e9f4739b`
- History/docs HEAD: `f7a135a0bc3d6f9b22fc17f63b838ed17bde0217` before this append-only record; it does not replace the source candidate.

## G6/G7 validation delta

- G6: `SIM_OBSERVABILITY_REGRESSION_READY`; schema/hash validation PASS; focused validation `51 passed`.
- Corrected full regression: candidate `396` collected, `4 failed`, `392 passed`; baseline `341` collected, `4 failed`, `337 passed`.
- Count difference: `55`, `EXPECTED_TEST_SUITE_EVOLUTION`; failed-node sets and non-empty stable signatures exactly match; classification `PASS_PROVEN_PREEXISTING`.
- Requirement-scoped classification: `53 / 21 / 32 / 0` (`HISTORICAL_DIAGNOSTIC_ONLY_NON_GATING` / `EXPLICITLY_QUALIFIED_BY_Q01` / `STILL_BLOCKING`).
- G7: fresh detached candidate/baseline source and test trees with the qualified interpreter; semantic equivalence to G6 PASS after excluding only `generated_at` and temporary-worktree paths.

## Next Action

`RUN_INDEPENDENT_S10_G8_REREVIEW`
