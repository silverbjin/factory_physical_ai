# Fix — TASK-SIM-010

- Result: NOT READY FOR INDEPENDENT RE-REVIEW
- Based on Review: `06_review.md`, `07_diagnosis.md`, `08_fix.md`
- Evidence: `results/simulation/SIM-010_observability_regression.json` (`SIM_OBSERVABILITY_REGRESSION_BLOCKED`)
- Regression: FAIL — `PROVEN_PREEXISTING` proven by identical four node IDs and non-empty normalized signatures at `6909c6cceb727598570f6e170ae8d1d293418c9a`
- Git history: NO HISTORY ACTION REQUIRED
- Next: BLOCKED

## Finding Results

| Finding | Severity | Status | Correction | Regression |
|---|---|---|---|---|
| SIM010-REV-001 | BLOCKER | FIXED | accepted-source binding, run extraction, and run validation were separated; SIM-003/SIM-006 are `NOT_REQUIRED`, while SIM-004/005/007/008/009 use explicit source-path extractors without synthetic defaults | PASS (focused 11 passed) |
| SIM010-REV-002 | HIGH | FIXED | current and detached-baseline executions now use the identical declared `python3 -m pytest -q -p no:cacheprovider` command; actual parsed signatures are non-empty and match | PROVEN_PREEXISTING |

## Remaining Gate

- Accepted run payloads fail R2–R7 validation without fabrication: required correlation/provenance/scenario/replay fields are absent from the extracted source subtrees. The generated Evidence remains fail-closed and reports `SIM_OBSERVABILITY_REGRESSION_BLOCKED`.
