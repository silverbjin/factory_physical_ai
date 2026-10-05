# A3 — stopped on a different earlier terminal failure

STATUS: STOP
FIRST_FAILING_INVARIANT: INITIAL_POSE_PUBLICATION_COMPLETES_WITHIN_EXISTING_BOUND
FIRST_FAILING_OBSERVATION: INITIAL_POSE_PUBLISH_FAILED
EVIDENCE:
- Invocation `4f960ad3b61643d78dfbb8c38e07853b`, source revision `adc05c55a76087f0230a2c42f94539ed35f3b741`.
- Executed once: `source .venv-sim/bin/activate`, then `DEMO_NO_WAIT=1 DEMO_VALIDATION_DIR="$PWD/results/demo/resolution/track_a/A3_run_01" bash demo_3d/scripts/01_normal_e2e_3d.sh`.
- Command and invocation exit code 1. `A3_run_01/gates.json`: A–F PASS, G FAIL, H PASS.
- `A3_run_01/runtime_observations.json#/measurements/started_at`: 2026-10-05T03:55:42.677Z (12:55:42.677 Asia/Seoul).
- Clock probes: timeout 5007.376 ms → timeout 5015.824 ms → success 2388.551 ms. Clock and prerequisites eventually ready; map_server and amcl active.
- `#/measurements/localization/probes/11`: initial_pose_publish timed_out=true, duration_ms=5049.381. `#/measurements/localization/initial_pose/published`: false.
- `#/measurements/session_readiness`: ready=false, stage=LOCALIZATION, error=INITIAL_POSE_PUBLISH_FAILED.
- `A3_run_01/normal_e2e_result.json#/execution/mission/timestamp`: 2026-10-05T03:56:44.361Z (12:56:44.361 Asia/Seoul); error.message=INITIAL_POSE_PUBLISH_FAILED.
- Navigation STARTUP was never called; no navigation goals sent. This is earlier than the selected archived FAIL's NAVIGATION_LIFECYCLE_START_FAILED.
- `A3_run_01/process_lifecycle.json`: cleanup survivors=[], elapsed_seconds=66.0, runner_exit_code=1. Canonical execution lifecycle.cleanup_complete=true.
- stdout/stderr preserved in A3_run_01_stdout.log and A3_run_01_stderr.log. All failed-run artifacts retained.

The earliest clock-probe timeout repeats, but it does not establish the lifecycle STARTUP failure: the live run terminates at a different earlier invariant. No second diagnostic run is allowed under this STOP condition. No source modification or logical correction was applied.

Missing proof for the reclassified A2 investigation:
1. Timestamped initial-pose client start/end, and TimeoutExpired partial stdout/stderr (the current _probe drops both on timeout).
2. Timestamped /initialpose subscription matching, publication, AMCL receipt/acceptance, and client exit. This separates discovery wait, publication/receipt, and CLI completion overhead without inferring failure from elapsed time alone.
3. For the original STARTUP failure, timestamped service availability, request send/receive, final activation/bond, response send/receive, and client termination. Existing probe records have durations but no absolute start/end or partial timeout output.

NEXT_GATE: A2 (reclassify as INITIAL_POSE_PUBLICATION_COMPLETES_WITHIN_EXISTING_BOUND); not executed in this turn because STOP forbids continuation. A4, B1–B4 and G-FINAL not entered. Track B's existing NOT_QUALIFIED output is unchanged and was not rerun.

Protected canonical/history integrity: `../protected_integrity_final.json` verifies all snapshotted files unchanged.
