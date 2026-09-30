# Fix — TASK-SIM-010

- Result: NOT READY FOR INDEPENDENT RE-REVIEW
- Based on Review: `06_review.md`, `07_diagnosis.md`, `09_fix.md`
- Evidence: `results/simulation/SIM-010_observability_regression.json` (`SIM_OBSERVABILITY_REGRESSION_BLOCKED`)
- Regression: FAIL — `PROVEN_PREEXISTING` with matching non-empty normalized signatures at `6909c6cceb727598570f6e170ae8d1d293418c9a`
- Git history: NO HISTORY ACTION REQUIRED
- Next: BLOCKED

## Finding Results

| Finding | Severity | Status | Correction | Regression |
|---|---|---|---|---|
| SIM010-REV-001 | BLOCKER | FIXED | normalized runs now bind only their own scenario parent plus explicit artifact context; run validation no longer requires a nested `scenarios` list or repeats artifact profile metadata in result children | PASS (focused 13 passed) |
| SIM010-REV-002 | HIGH | FIXED | detached-baseline full regression continues to prove the four failures are `PROVEN_PREEXISTING` with stable non-empty signatures | PROVEN_PREEXISTING |

## Remaining Gate

- Fail-closed predecessor-field gaps remain in accepted run data: SIM-004 Gazebo bridge/launch/timing fields, SIM-005 `trace_id`, SIM-007 normalized profile run provenance/correlation, and SIM-009 source hashes/simulator provenance plus selected failure/verification fields. Downstream replay reports `NO_VALIDATED_DETERMINISTIC_RUNS`; physics has validated Gazebo but no validated MuJoCo row.
