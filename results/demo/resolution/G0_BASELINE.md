# G0 — frozen baseline

STATUS: PASS
FIRST_FAILING_INVARIANT: NONE (baseline identified)
EVIDENCE:
- Starting HEAD: `adc05c55a76087f0230a2c42f94539ed35f3b741`.
- Starting `git status --short`: empty (clean).
- Latest archived Normal PASS: `results/demo/runs/e04fbe08b3384f21a34e7a80fe562d1b/gates.json`; A–H true. Invocation `e04fbe08b3384f21a34e7a80fe562d1b`, runner exit 0. Generated 2026-10-05T01:20:48.273Z.
- Latest archived Gate G Normal FAIL: `results/demo/runs/3a872aa7c7b640dcab449dbf2571737c/gates.json`; A–F true, G false, H true. Invocation `3a872aa7c7b640dcab449dbf2571737c`, runner exit 1. Generated 2026-10-05T01:24:05.736Z.
- Both selected execution artifacts record `source_git_sha=c2951b70241ed0c6abcc02e47bcc1321639040b9`; this differs from current HEAD. No assertion of current-HEAD live reproduction yet.
- Current qualification: `results/simulation/SIM-E2E_qualification.json#/decision = SIM_E2E_NOT_QUALIFIED`; recorded evaluation HEAD a78ee58e2cd151ef72811d5995a3f275a0a5434d. This is existing output, not a fresh verifier execution.
- Current demo version: `demo_3d/VERSION = 1.6`.
- Protected-file SHA256 snapshot: `results/demo/resolution/protected_hashes_baseline.json`.
NEXT_GATE: A1
