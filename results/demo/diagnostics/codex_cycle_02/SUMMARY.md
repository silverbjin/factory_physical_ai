# Live SIM-008 3D validation

Gate A: FAIL
Gate B: FAIL
Gate C: FAIL
Gate D: FAIL
Gate E: FAIL
Gate F: FAIL
Gate G: FAIL
Gate H: PASS

DEMO_VISUALIZATION_AUGMENTATION: resolved headless world plus installed SceneBroadcaster.
Mission uses the unchanged SIM-008 runner and Nav2 launch. Accepted Evidence is preserved.
Screenshot: None
GUI scene receive log: False
Exception: Exact live runtime SDF is unavailable

ROOT_CAUSE_HYPOTHESIS: observer copied Nav2 temporary SDF too early.
ACTUAL_RESULT: Exact live runtime SDF is unavailable; owned processes fully cleaned; protected hashes identical.
FAIL
NEXT_DECISION: bounded file-generation wait in observer only. No new world/server fix.
