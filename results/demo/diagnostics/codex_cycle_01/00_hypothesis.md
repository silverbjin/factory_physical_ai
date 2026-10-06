ROOT_CAUSE_HYPOTHESIS: v1.5 substring check sees conditional SceneBroadcaster and skips injection; headless xacro removes it.
EXPECTED_RESULT: direct unconditional control passes, old worktree remains conditional, runtime has no scene plugin/service.
SMALLEST_CHANGE: diagnostic copy only.
