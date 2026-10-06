Classification: NAV2_WORLD_PREPROCESSING_DROPS_SCENE_BROADCASTER
Direct control scene service: True
SOURCE_HAS_SCENE=true (conditional)
SOURCE_DIRECT_HAS_SCENE=false
RUNTIME_TEMP_HAS_SCENE=False
Runner exit: 0
The source is unchanged because v1.5 detects the conditional plugin by substring. Nav2 xacro removes that block with headless:=True.

Evidence supplement: 04_runtime_world.sdf was captured independently while the server was live after Ruby rewrote argv to a single process title. proc_180781.json records the live path. Source and runtime SHA256/plugin lists are in 05_plugins.txt.
PASS: diagnosis established; FAIL: visualization gates C/D.
NEXT_DECISION: resolve headless xacro first, then inject into resolved demo-only world; verify second Nav2 transformation is idempotent.

EVIDENCE_SUPPORTING_IT: installed plugin example/library inspection, direct scene response, actual Nav2 command and captured runtime SDF.
ACTUAL_RESULT: direct scene passes; old worktree plugin remained conditional and runtime temp lacks it; canonical mission passes.
