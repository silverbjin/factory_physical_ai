ROOT_CAUSE_HYPOTHESIS: headless xacro removes the only conditional SceneBroadcaster. The augmentation helper previously mistook it for an unconditional plugin.
EVIDENCE_SUPPORTING_IT: cycle 01 direct control returns scene and ECU; real Nav2 source retains conditional plugin; actual /tmp/nav2_z1ioeq_p.sdf omits it; runner success.
SMALLEST_CHANGE: resolve headless xacro first, add installed plugin at world scope in demo worktree; eliminate unintended --help mission; normalize rewritten Gazebo process title.
EXPECTED_RESULT: Nav2 consumes augmented worktree world and generates runtime SDF with active plugin; scene contains ECU; matched GUI receives it; unchanged mission completes.
