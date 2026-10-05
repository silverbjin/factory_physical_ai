ROOT_CAUSE_HYPOTHESIS: scene and rendering are correct; repeated screenshot captures may add contention during an already bounded Nav2 lifecycle request.
EVIDENCE_SUPPORTING_IT: A–F and H pass; mission fails NAVIGATION_LIFECYCLE_START_FAILED; logs show navigation activation progressing to docking_server before cleanup, without plugin/render errors. Prior cycle 03 succeeds. Screenshot capture ran repeatedly throughout this failed mission.
SMALLEST_CHANGE: stop screenshot capture after the first rendered frame, rather than continue it for the entire mission. Also fix process scanning to shlex only rewritten single-token Gazebo titles; preflight encountered an unrelated shell argv quotation.
EXPECTED_RESULT: unchanged mission bounds complete with lower observation overhead; all live 3D gates remain true.
ACTUAL_RESULT: this cycle failed Gate G and is retained; next run tests the observation-only reduction.
FAIL
NEXT_DECISION: clean final run, without concurrent static validation or repeated screenshots after proof.
