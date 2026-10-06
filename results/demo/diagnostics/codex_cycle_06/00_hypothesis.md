ROOT_CAUSE_HYPOTHESIS: the proven scene fix remains valid; invocation isolation and failure cleanup need explicit lifecycle guarantees.
EVIDENCE_SUPPORTING_IT: independent review found reused output paths and unguarded preparation; regression tests reproduce stale PASS and leaked worktree.
SMALLEST_CHANGE: unique default output, single-invocation lock, pending/complete/failed manifest, guarded worktree preparation and source copying, ownership sampling through shutdown. No scene/world/GUI configuration or mission change.
EXPECTED_RESULT: the same real rendered Normal execution passes A–H from the corrected package; completed-run verifier accepts only current complete metadata.

ACTUAL_RESULT: A–F/H PASS, G FAIL: SIMULATION_CLOCK_UNAVAILABLE. ROS bridge/Nav2 children did not emit startup logs; scene model count 2 (before robot spawning), GUI renders Depot/ECU. No recorded owned processes remain.
FAIL
NEXT_DECISION: rerun unchanged with independent process/thread and live-clock sampling to diagnose ROS startup rather than change mission/scene.
