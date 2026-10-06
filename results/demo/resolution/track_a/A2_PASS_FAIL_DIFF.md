# A2 — one PASS / one FAIL comparison

STATUS: PASS
FIRST_FAILING_INVARIANT: NAVIGATION_LIFECYCLE_START_RESPONSE_WITHIN_EXISTING_BOUND
FIRST_DIVERGENT_OBSERVATION: FIRST_ROS_CLOCK_PROBE_TIMEOUT
EVIDENCE: `A2_PASS_FAIL_DIFF.json` contains the selected run paths/IDs and exact probe records.

| Measurement | PASS | FAIL |
|---|---|---|
| source_git_sha | c2951b70241ed0c6abcc02e47bcc1321639040b9 | same |
| FastDDS profile SHA256 | 76b59e79c49e05368a45d794e8f8985415f52bd0a2679230775cc655342aa6c3 | same |
| ROS_DOMAIN_ID | 104 | 16 |
| GZ_PARTITION | sim004-113b9587fabd | sim004-5ae6ee9761cf |
| First clock probe | 4010.877 ms, success | 5009.655 ms, timeout |
| Eventual clock / prerequisites / map_server / amcl / map→odom | ready | ready |
| manage_nodes STARTUP | 8154.098 ms, returncode 0 | 10013.583 ms, timeout |
| bt_navigator + action readiness | true | not measured after startup failure |
| Navigation goals | two accepted, SUCCEEDED | none sent |
| Final verification | pass | absent |
| Mission | success | NAVIGATION_LIFECYCLE_START_FAILED |
| Cleanup / residual processes | true / 0 | true / 0 |
| G subconditions (exit, READY, cleanup, survivors) | true,true,true,true | false,false,true,true |

PASS timeline (ordered probes; probe absolute start/end timestamps are not recorded):
launch 2026-10-05T01:19:28.223Z → clock success → map/scan/odom/TF ready → map_server/amcl configure+activate → initialpose published → map→odom ready → navigation STARTUP response → bt_navigator active + action listed → source goal accepted/SUCCEEDED → source verification pass → destination goal accepted/SUCCEEDED → final verification pass → mission success 01:20:48.156Z → cleanup complete.

FAIL timeline:
launch 2026-10-05T01:23:03.365Z → FIRST DIVERGENCE: first clock probe timeout → next clock probe success → prerequisites ready → map_server/amcl configure+activate → initialpose published → first map→odom probe timeout → next TF probe success → navigation STARTUP call timeout → mission fails 01:24:05.605Z → cleanup complete. Server log shows STARTUP processing at epoch 1791163440.129038323 and bt_navigator bond at 1791163445.599664571, just before mission failure, but no service response acknowledgment.

Different domain/partition values are expected per-invocation isolation identities; they are not alone evidence of environmental inconsistency. Earlier bounded probe retries eventually satisfy clock and TF invariants. The first terminal invariant is the STARTUP client response bound. The earliest transient clock difference is an observation, not a proven cause of that terminal failure.

Principal A3 hypothesis: the FAIL pattern (first clock timeout followed by eventual readiness and STARTUP client timeout) is reproducible. Existing evidence does not prove whether service discovery, request dispatch, server activation, or response delivery consumed the client bound. No correction is justified yet.
NEXT_GATE: A3
