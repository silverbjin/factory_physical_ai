# Gazebo 3D repair implementation plan

Goal: Prove the actual SIM-008 mission, scene publication, GUI rendering and cleanup before packaging.
Architecture: Retain the canonical runner in a disposable detached worktree. Resolve headless xacro before adding the installed SceneBroadcaster to the resolved demo SDF. Follow the runner-owned server and capture live provenance, transport, scene and GUI evidence.
Constraints: Only demo_3d and results/demo modifications; no canonical writes, commits, installed ROS changes, startup pauses or unrelated process termination.

1. Regression: real headless xacro must preserve an unconditional SceneBroadcaster after augmentation. Test the known canonical conditional input; demonstrate old helper fails.
2. Fix the conditional detection and remove the unsafe Normal --help execution. Normalize Gazebo's rewritten process title for discovery; verify both argv forms.
3. Run the package with live evidence collection. Store runtime SDF, /proc metadata, scene response, GUI logs and screenshot if possible. Require A–H and mission completion; revise only failing boundary.
4. Consolidate documentation, eliminate obsolete wrapper/pause configuration, version after proof, run clean final package validation, zip.

Review focus: conditional plugins; process title rewritten by Ruby; canonical writes via --help probes; server transitions; exception cleanup of owned processes.
Execution: inline, as explicitly requested. No per-cycle approval or commits. User instructions override skill handoff/commit requirements.
