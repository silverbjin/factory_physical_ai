# Remaining Issues — Final Resolution

## 1. Executive Result

NORMAL_RUNTIME_STABLE: YES

CANONICAL_SIM_E2E_QUALIFIED: YES

NAV_TIMEOUT_POLICY_PRESERVED: YES

VERIFY_UNCERTAIN_POLICY_PRESERVED: YES

CANONICAL_HISTORY_PRESERVED: YES

FINAL_STATUS: RESOLVED

## 2. Track A Root Cause

FIRST OBSERVED FAILURE: INITIAL_POSE_PUBLISH_FAILED at approximately5.049s, followed by earlier/later live frontiers preserved in the diagnostic history.

ACTUAL ROOT CAUSE: cold ros2 CLI participant/startup/discovery/keep-alive costs were charged to bounded bootstrap completion; valid multi-frame Gazebo stats were rejected by whole-output JSON parsing. Later integrated runs exposed pathname-before-complete-world readiness and a pristine-Git-status check incompatible with explicitly authorized forward-only canonical artifacts.

WHY PASS/FAIL VARIED: client/discovery overhead and queued stats frame count vary; generated SDF pathname can be visible while its file is empty. No simulated mission success was fabricated.

FIX: run-owned warmed bootstrap clients with explicit readiness and original5s/10s bounds; complete framed stats validation; event-driven complete world XML readiness within original3s; GateH admits only exact independently qualified new successor paths while hashing every protected file and rejecting tracked changes/unknown files.

WHY THIS FIX IS MINIMAL: each correction followed its own captured failure/control/RED proof, preserves navigation/mission/retry semantics, and changes only the proven boundary. No timeout increases, arbitrary sleeps, SIGSTOP, broadpkill, or historical accepted rewrites. Independent review and negative/tamper checks passed.

## 3. Track A Stability Proof

Five consecutive final-version runs, identical source manifests, all A–H PASS:

| Run | Invocation ID | A–H | Exit | Seconds |
|---|---|---|---|---|
| 1 | 67581794853847e4927e1f4fc1b96f13 | PASS | 0 | 85.613 |
| 2 | 9f53cae822114cf0ae8c5a947fcdd72f | PASS | 0 | 87.332 |
| 3 | 86f50220f4cb4af98f7e1364e5a62302 | PASS | 0 | 83.722 |
| 4 | 7ad3f6f13e2447079f666e7421f8ed83 | PASS | 0 | 82.977 |
| 5 | 13a42c913f0446cb9051a244919dbb41 | PASS | 0 | 81.712 |

Exact evidence: `results/demo/resolution/track_a/continuation/confirmed_five_run_stability.json` and each `confirmed_stability_01`…`05` directory. Final helper SHA256 `a6a044f6f4f81989e6cbe6f94da0c4b15761bae1d84cd788b80396715c9dbcf0`; all other runtime hashes and root/isolated-worktree matches appear in NORMAL_STABILITY_REPORT.md. Original successes, failed cycles and mixed-version samples remain archived and excluded from the final counter.

## 4. Track B Initial Qualification Failure

Real verifier initially returned SIM_E2E_NOT_QUALIFIED. All eight immutable predecessor bindings validated, but SIM-007 genuinely records BLOCKED and historical SIM-010 lacks unique predicate-source ownership. Twenty historical semantic values passing could not supply absent acceptance authority.

## 5. Track B Predicate Closure

| Predicate/frontier | Root cause | Correction | Result |
|---|---|---|---|
| SIM-007 READY | Accepted historical BLOCKED | New canonical four-profile execution, independent review, new R01 acceptance | READY |
| Unique predicate ownership | Historical index insufficient | Fresh R01 source index, all 8 historical bindings/all 20owners | PASS |
| Regression green | Stale provenance fixtures and SIGINT cleanup race | Exact reviewed Git fixture inputs; protected cleanup boundary | 568PASS |
| Manipulation dispatch | Fixture waypoint and bench goal namespaces mixed | Approved Navigation fixture route plus measured MuJoCo transfer objective | PASS |
| Semantic identity/order | Correlation and chronology not reconstructed | Request/action/trace, timestamp, destination and observation-hash negative checks | PASS |
| Complete manifest | Legacyconfig assets omitted | Bothconfig/configs captured in reviewed106-file manifest | PASS |
| Navigation execution | Cold CLI overhead consumes5s budget | Warm owned ActionClient, same5s, matchedUUIDterminal4/error0 | PASS |
| Real-xacro regression | ROS Python paths discarded | Preserve inheritedPYTHONPATH and installedJazzyenvironment | PASS |

Forward-only correction type: FORWARD_ONLY_NEW_EVIDENCE under SIM-E2E-SUCCESSOR-V1. New independent acceptance is exact candidate HEAD + reviewed working-tree source manifest + EvidenceSHA; it does not claim uncommitted source is an accepted Git blob. No demo Evidence is consumed. Component mission requests explicitly declare60s within the unchanged1..60s contract; their actual0.009/1.414/0.155s bodies also meet the10s fixture default. Component actions remain5s and Normal mission remains30s.

## 6. Final Canonical Qualification

SIM_E2E_QUALIFIED

Canonical output: `results/simulation/SIM-E2E-R01_qualification.json`. SHA256: `f82c1241a1ac470bff467516592a5179eaba2b510dcd2c887cb5b11538516810`. Candidate HEAD: `82b9a5e57ffd871a29b5ea60cb531e1b75e7631b`.

Fresh final actual verifier output: `results/demo/resolution/track_b/continuation/C4_final_qualification.json`; stdout SIM_E2E_QUALIFIED, exit0, empty stderr, all 20 green. Exact source/evidence/acceptance/log hashes and full matrix appear in CANONICAL_E2E_QUALIFICATION_REPORT.md. Independent review: `independent_canonical_review_final.json`, ACCEPT/no findings; full repository pytest: 568 passed in 59.62s, exit0.

## 7. Regression

Navigation timeout: SIM009-NAV-TIMEOUT-RETRY, unknown→RETRY, expected=decisionRETRY, pass/within_budget/cleanup_complete=true.

Verification uncertain: uncertain→RECONCILE, expected=decision=routeRECONCILE, mission_state=reconciling, mission_success_committed=false, verification_verdict=uncertain, pass=true.

Final Normal, additional to five-run proof: invocation `2d5fd89ecf204653b8b59b8fdb9ca8ef`, all A–H PASS, exit 0; `results/demo/resolution/track_c/final_normal_integrated/`.

Static validation:25 Python files compile, eight bash scripts, bash -n, git diff --check PASS. Raw policy/assertion/source identity/logs reside under `results/demo/resolution/track_c/`; tests were not skipped.

## 8. Integrity

All 236 historical protected files remain byte-identical. All eight accepted predecessor Evidence hashes equal their acceptance and accepted Git blobs. Exact per-file original/current SHA256 and seven new forward-only artifact hashes: `results/demo/resolution/track_d/final_integrity.json`.

Forward-only artifacts:

- `results/simulation/SIM-E2E-R01_qualification.json`: `f82c1241a1ac470bff467516592a5179eaba2b510dcd2c887cb5b11538516810`
- `results/simulation/SIM-007-R01_mission_integration.json`: `68bfa79e46583ea863e818d28977adf65cff47cb39fc729ad15b7fd1c5d3f508`
- `results/simulation/SIM-010-R01_observability_regression.json`: `69c789b03215005bc6e2cd3a17020ffb0f09e7b0ed3f07a3d6dc93ed00c01090`
- `results/simulation/SIM-010-R01_observability_regression_logs/pytest_stdout.log`: `af065f3e18f2792b3fc78bd00414567a90a479cb8cf3b2bf91953223fdf9f275`
- `results/simulation/SIM-010-R01_observability_regression_logs/pytest_stderr.log`: `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`
- `results/reviews/SIM-010-R01_acceptance.json`: `425dbe0d87a5e603aecdd7966548dc5357c03e3761f6acd3aca8ad9c10c8064c`
- `results/reviews/SIM-007-R01_acceptance.json`: `394ad1385f96d6d710c4cc37908e23f65009a807f03b81d08eeb8de2e929b005`

The declaration is `configs/simulation/e2e_successor_chain_v1.json`; historical contracts/acceptances/taskhistory were not overwritten. Legacy historical qualification remains NOT_QUALIFIED, openly recorded alongside the independently accepted additive current chain. Owned orphan from a failed canonical attempt was identified by exactPID/startticks/domain/partition/profile and terminated individually; unrelated preexisting server remained untouched. Failed evidence remains preserved.

## 9. Remaining Limitations

No unresolved blocker remains for the requested outcomes. Qualification is bound to the recorded candidateHEAD and106-file canonical source manifest; later source/HEAD changes require a new valid review binding. Gazebo remains the integrated world and MuJoCo a component bench; physical/training/hardware authorizations remainfalse.
